"""Cross-app business logic for event extraction and management."""

import json
import logging

import tiktoken
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
from openai import APIConnectionError, OpenAI, OpenAIError, RateLimitError
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from poc.models import (
    Case,
    CaseLitigant,
    LitigantRole,
    ParsedEmail,
    ParsedEmailAttachment,
    UploadedFile,
)
from poc.utils import (
    extract_text_from_csv,
    extract_text_from_docx,
    extract_text_from_pdf,
    extract_text_from_pptx,
    extract_text_from_txt,
    extract_text_from_xlsx,
)

from .models import CandidateEvent, Timeline, TimelineEvent, TimelineExhibit

logger = logging.getLogger(__name__)


def get_case_details(case: Case, minimal: bool = False) -> str:
    """Retrieves the case details to be used for event extraction.

    Args:
        case (Case): The case for which to retrieve details.
        minimal (bool): Whether to retrieve minimal case details.

    Returns:
        str: The case details to be used for event extraction.
    """
    case_details = f"Case Title: {case.title}\n"

    if case.case_number:
        case_details += f"Case Number: {case.case_number}\n"

    if not minimal:
        case_details += f"Case Description: {case.description}\n"

    return case_details


def get_litigants_info(case: Case) -> str:
    """Retrieves the litigants information for the case.

    Args:
        case (Case): The case for which to retrieve litigants information.
    Returns:
        str: The litigants information for the case.
    """
    litigant_info = ""
    litigant_roles = LitigantRole.objects.all()
    for role in litigant_roles:
        case_litigants = CaseLitigant.objects.filter(case=case, role=role)
        if case_litigants.exists():
            litigant_info += f"{role.name.upper()}S:\n"
            for case_litigant in case_litigants:
                if case_litigant.is_our_client:
                    litigant_info += "(Our Client)\n"

                litigant_info += (
                    f"Name: {case_litigant.litigant.name}\n"
                    f"Email: {case_litigant.litigant.email}\n"
                    f"Phone: {case_litigant.litigant.phone}\n"
                    "---\n"
                )

    return litigant_info


def get_uploaded_file_content(uploaded_file: UploadedFile) -> str:
    """Retrieves the content from an uploaded file.

    Args:
        uploaded_file (UploadedFile): The uploaded file to retrieve content from.
    Returns:
        str: The content of the uploaded file.
    """
    if uploaded_file.file_extension == "eml":
        return get_parsed_email_content(uploaded_file.parsed_email)

    content = (
        "[Document]\n"
        f"ID: {uploaded_file.id}\n"
        f"Filename: {uploaded_file.filename}\n"
        f"Uploaded On: {uploaded_file.created_at}\n"
        # todo: include published date if available (may require additional field in UploadedFile model and handling during file upload)
        "Content:\n"
    )

    file_reader_func = None

    if uploaded_file.file_extension == "txt":
        file_reader_func = extract_text_from_txt
    elif uploaded_file.file_extension == "csv":
        file_reader_func = extract_text_from_csv
    elif uploaded_file.file_extension in [
        "xlsx",
        "xls",
    ]:
        file_reader_func = extract_text_from_xlsx
    elif uploaded_file.file_extension in [
        "docx",
        "doc",
    ]:
        file_reader_func = extract_text_from_docx
    elif uploaded_file.file_extension in [
        "pptx",
        "ppt",
    ]:
        file_reader_func = extract_text_from_pptx
    elif uploaded_file.file_extension == "pdf":
        file_reader_func = extract_text_from_pdf
    else:
        logger.warning(
            f"Unsupported file type '{uploaded_file.file_extension}' for uploaded file ID {uploaded_file.id}. Skipping content extraction."
        )

    if file_reader_func:
        for chunk in file_reader_func(uploaded_file.file):
            content += chunk

    content += f"---[End of Document ID: {uploaded_file.id}]---\n"
    return content


def get_parsed_email_content(parsed_email: ParsedEmail) -> str:
    """Retrieves the content from a parsed email, including its attachments.

    Args:
        parsed_email (ParsedEmail): The parsed email to retrieve content from.
    Returns:
        str: The aggregated content from a parsed email, including its attachments.
    """
    content = ""
    content += (
        "[Email]\n"
        f"ID: {parsed_email.id}\n"
        f"Subject: {parsed_email.subject}\n"
        f"From: {parsed_email.sender}\n"
        f"To: {parsed_email.to_recipients}\n"
        f"Cc: {parsed_email.cc_recipients}\n"
        f"Sent On: {parsed_email.sent_on}\n"
        "Content:\n"
        f"{parsed_email.cleaned_body}\n"
    )
    for attachment in parsed_email.parsed_attachments.all():
        content += get_parsed_email_attachment_content(attachment)

    content += f"---[End of Email ID: {parsed_email.id}]---\n"
    return content


def get_parsed_email_attachment_content(attachment: ParsedEmailAttachment) -> str:
    """Retrieves the content from a parsed email attachment.

    Args:
        attachment (ParsedEmailAttachment): The parsed email attachment to retrieve content from.
    Returns:
        str: The content of the parsed email attachment.
    """
    content = (
        "[Email Attachment]\n"
        f"ID: {attachment.id}\n"
        f"Filename: {attachment.filename}\n"
        f"Content Type: {attachment.content_type}\n"
        f"Content:\n"
    )

    file_reader_func = None

    if attachment.content_type == "text/plain":
        file_reader_func = extract_text_from_txt
    elif attachment.content_type == "text/csv":
        file_reader_func = extract_text_from_csv
    elif attachment.content_type in [
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-excel",
    ]:
        file_reader_func = extract_text_from_xlsx
    elif attachment.content_type in [
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
    ]:
        file_reader_func = extract_text_from_docx
    elif attachment.content_type in [
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/vnd.ms-powerpoint",
    ]:
        file_reader_func = extract_text_from_pptx
    elif attachment.content_type == "application/pdf":
        file_reader_func = extract_text_from_pdf
    else:
        logger.warning(
            f"Unsupported content type '{attachment.content_type}' for attachment ID {attachment.id}. Skipping content extraction."
        )

    if file_reader_func:
        for chunk in file_reader_func(attachment.file):
            content += chunk

    content += f"---[End of Attachment ID: {attachment.id}]---\n"
    return content


class CandidateEventExtractor:
    def __init__(self, timeline_exhibit: TimelineExhibit):
        self.timeline_exhibit = timeline_exhibit
        self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
        prompt_filepath = settings.BASE_DIR.joinpath(
            "events", "docs", "prompts", "timeline_pass_1_candidate_extraction.md"
        )
        with open(prompt_filepath, "r") as file:
            self.prompt_instructions = file.read()

    def _get_response_text_format(self) -> dict:
        """Defines the expected response format for candidate event extraction from the LLM.

        Returns:
            dict: The expected response format for candidate event extraction.
        """
        return {
            "format": {
                "type": "json_schema",
                "name": "candidate_events",
                "schema": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "events": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "properties": {
                                    "candidate_id": {"type": "string"},
                                    "action_phrase": {"type": "string"},
                                    "raw_description": {"type": "string"},
                                    "event_date": {"type": "string"},
                                    "date_confidence": {
                                        "type": "string",
                                        "enum": ["explicit", "inferred", "weak"],
                                    },
                                    "actors": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                    },
                                    "evidence_excerpt": {"type": "string"},
                                    "confidence": {"type": "number"},
                                    "source": {
                                        "type": "object",
                                        "additionalProperties": False,
                                        "properties": {
                                            "type": {
                                                "type": "string",
                                                "enum": [
                                                    "document",
                                                    "email",
                                                    "attachment",
                                                ],
                                            },
                                            "id": {"type": "number"},
                                        },
                                        "required": ["type", "id"],
                                    },
                                },
                                "required": [
                                    "candidate_id",
                                    "action_phrase",
                                    "raw_description",
                                    "event_date",
                                    "date_confidence",
                                    "actors",
                                    "evidence_excerpt",
                                    "confidence",
                                    "source",
                                ],
                            },
                        }
                    },
                    "required": ["events"],
                },
            }
        }

    def _get_content(self) -> str:
        content = ""
        case = self.timeline_exhibit.timeline.case
        content += get_case_details(case, minimal=True)
        content += get_litigants_info(case)
        content += get_uploaded_file_content(self.timeline_exhibit.exhibit)

        return content

    @retry(
        # Exponential backoff: 2s, 4s, 8s, 16s... up to a max of 60s
        wait=wait_exponential(multiplier=1, min=2, max=60),
        # Stop after 5 failed attempts
        stop=stop_after_attempt(5),
        # Only retry on specific network or rate-limit errors
        retry=retry_if_exception_type((RateLimitError, APIConnectionError)),
        # Log the attempt details before sleeping
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    def _extract_candidate_events(self, content: str) -> list[dict]:
        try:
            encoding = tiktoken.encoding_for_model("gpt-4o")
            tokens = encoding.encode(content)
            logger.info(
                f"Extracting candidate events for timeline exhibit ID {self.timeline_exhibit.id}. Total tokens in content: {len(tokens)}"
            )

            response = self.openai_client.responses.create(
                model="gpt-5-mini",
                input=[
                    {
                        "role": "system",
                        "content": self.prompt_instructions,
                    },
                    {"role": "user", "content": content},
                ],
                reasoning={
                    "effort": "minimal",
                },
                text=self._get_response_text_format(),
            )

            if response.output_text:
                return json.loads(response.output_text).get("events", [])

            return []
        except OpenAIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(
                f"JSON decoding error: {e}. Response text: {response.output_text}"
            )
            raise ValueError(
                "Failed to parse candidate events from LLM response due to invalid JSON format."
            )

    def _save_candidate_events(
        self, candidate_events: list[dict], dry_run: bool = False
    ) -> list[CandidateEvent]:
        """Transforms the list of candidate event dictionaries into a list of CandidateEvent objects.

        Args:
            candidate_events (list[dict]): A list of dictionaries representing candidate events extracted from the LLM response.
            dry_run (bool): If True, the candidate events will not be saved to the database.
        Returns:
            list[CandidateEvent]: A list of CandidateEvent objects created from the input dictionaries. Not saved to the database yet.
        """
        saved_events = []
        for event_data in candidate_events:
            if not isinstance(event_data, dict):
                logger.warning(
                    f"Skipping invalid candidate event data (not a dictionary): {event_data}"
                )
                continue

            event_date_str = event_data.get("event_date")
            event_date = timezone.now()
            if event_date_str:
                try:
                    event_date = timezone.datetime.fromisoformat(event_date_str)
                    if event_date.tzinfo is None:
                        event_date = timezone.make_aware(event_date)
                except ValueError as error:
                    logger.info(
                        f"Failed to parse event_date '{event_date_str}' for candidate event '{event_data.get('raw_description')}'. Error: {error}. Defaulting to current datetime."
                    )

            candidate_event = CandidateEvent(
                action_phrase=event_data.get("action_phrase", ""),
                raw_description=event_data.get("raw_description", ""),
                event_date=event_date,
                date_confidence=event_data.get("date_confidence", "unknown"),
                actors=event_data.get("actors", []),
                evidence_excerpt=event_data.get("evidence_excerpt", ""),
                confidence=event_data.get("confidence", 0.0),
                source=event_data.get("source", {}),
                timeline_exhibit=self.timeline_exhibit,
            )

            try:
                candidate_event.full_clean()
                if not dry_run:
                    candidate_event.save()

                saved_events.append(candidate_event)
            except ValidationError as e:
                logger.error(
                    f"Validation error for candidate event '{event_data}': {e}"
                )
                continue

        return saved_events

    def run(self, dry: bool = False) -> list[dict]:
        """Main method to run the candidate event extraction process for the timeline exhibit.

        Args:
            dry (bool): If True, candidate events will not be saved to the database.

        Returns:
            list[CandidateEvent]: A list of CandidateEvent objects created from the input dictionaries. Not saved to the database if dry=True.
        """
        content = self._get_content()
        if len(content.strip()) > 255:
            logger.debug(f"Content: {content[:255]}... [truncated]")
        else:
            logger.debug(f"Content: {content}")

        events_data = self._extract_candidate_events(content)
        logger.debug(f"Extracted candidate events data: {events_data}")
        candidate_events = self._save_candidate_events(events_data, dry_run=dry)
        logger.debug(
            f"No. of candidate events: {len(candidate_events)} from LLM, {len(candidate_events)} saved to the database (dry_run={dry})"
        )
        return candidate_events


class TimelineEventReconstructor:
    def __init__(self, timeline: Timeline):
        self.timeline = timeline
        prompt_filepath = settings.BASE_DIR.joinpath(
            "events", "docs", "prompts", "timeline_pass_2_event_reconstruction.md"
        )
        with open(prompt_filepath, "r") as file:
            self.prompt_instructions = file.read()

    def _get_response_text_format(self) -> dict:
        """Defines the expected response format for event reconstruction from the LLM.

        Returns:
            dict: The expected response format for event reconstruction.
        """
        return {
            "format": {
                "type": "json_schema",
                "name": "reconstructed_events",
                "schema": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "events": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "properties": {
                                    "title": {"type": "string"},
                                    "description": {"type": "string"},
                                    "event_date": {"type": "string"},
                                    "place": {"type": "string"},
                                    "action_phrase": {"type": "string"},
                                    "actors": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                    },
                                    "source": {
                                        "type": "object",
                                        "additionalProperties": False,
                                        "properties": {
                                            "type": {
                                                "type": "string",
                                                "enum": [
                                                    "document",
                                                    "email",
                                                    "attachment",
                                                ],
                                            },
                                            "id": {"type": "number"},
                                        },
                                        "required": ["type", "id"],
                                    },
                                },
                                "required": [
                                    "title",
                                    "description",
                                    "event_date",
                                    "place",
                                    "action_phrase",
                                    "actors",
                                    "source",
                                ],
                            },
                        }
                    },
                    "required": ["events"],
                },
            }
        }

    def _get_content(self) -> list[dict]:
        """Aggregates the content from all candidate events associated with the timeline to be used for event reconstruction.

        Returns:
            list[dict]: A list of dictionaries representing the candidate events and their details to be used for event reconstruction.
        """
        candidate_events = CandidateEvent.objects.filter(
            timeline_exhibit__timeline=self.timeline
        )

        return [
            {
                "id": candidate_event.id,
                "action_phrase": candidate_event.action_phrase,
                "raw_description": candidate_event.raw_description,
                "event_date": candidate_event.event_date.isoformat(),
                "date_confidence": candidate_event.date_confidence,
                "actors": candidate_event.actors,
                "evidence_excerpt": candidate_event.evidence_excerpt,
                "confidence": candidate_event.confidence,
                "source": candidate_event.source,
            }
            for candidate_event in candidate_events
        ]

    @retry(
        # Exponential backoff: 2s, 4s, 8s, 16s... up to a max of 60s
        wait=wait_exponential(multiplier=1, min=2, max=60),
        # Stop after 5 failed attempts
        stop=stop_after_attempt(5),
        # Only retry on specific network or rate-limit errors
        retry=retry_if_exception_type((RateLimitError, APIConnectionError)),
        # Log the attempt details before sleeping
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    def _reconstruct_events(self, candidate_events: list[dict]) -> list[dict]:
        """Reconstructs the events for the timeline by aggregating the candidate events using LLM.

        Args:
            candidate_events (list[dict]): A list of dictionaries representing the candidate events to be used for event reconstruction.
        Returns:
            list[dict]: A list of dictionaries representing the reconstructed events.
        """
        try:
            content = json.dumps(candidate_events)
            encoding = tiktoken.encoding_for_model("gpt-4o")
            tokens = encoding.encode(content)
            logger.info(
                f"Reconstructing events for timeline ID {self.timeline.id}. Total tokens in content: {len(tokens)}"
            )

            response = OpenAI(api_key=settings.OPENAI_API_KEY).responses.create(
                model="gpt-5-mini",
                input=[
                    {
                        "role": "system",
                        "content": self.prompt_instructions,
                    },
                    {"role": "user", "content": content},
                ],
            )

            if response.output_text:
                return json.loads(response.output_text).get("events", [])

            return []
        except OpenAIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(
                f"JSON decoding error: {e}. Response text: {response.output_text}"
            )
            raise ValueError(
                "Failed to parse events from candidate events due to invalid JSON format in the LLM response."
            )

    def _save_reconstructed_events(
        self, events_data: list[dict], dry_run: bool = False
    ) -> list[TimelineEvent]:
        """Transforms the list of reconstructed event dictionaries into a list of TimelineEvent objects.

        Args:
            events_data (list[dict]): A list of dictionaries representing reconstructed events extracted from the LLM response.
            dry_run (bool): If True, the reconstructed events will not be saved to the database.
        Returns:
            list[TimelineEvent]: A list of TimelineEvent objects created from the input dictionaries. Not saved to the database yet.
        """
        saved_events = []
        for event_data in events_data:
            if not isinstance(event_data, dict):
                logger.warning(
                    f"Skipping invalid event data (not a dictionary): {event_data}"
                )
                continue

            event_date_str = event_data.get("event_date")
            event_date = timezone.now()
            if event_date_str:
                try:
                    event_date = timezone.datetime.fromisoformat(event_date_str)
                    if event_date.tzinfo is None:
                        event_date = timezone.make_aware(event_date)
                except ValueError as error:
                    logger.info(
                        f"Failed to parse event_date '{event_date_str}' for event '{event_data.get('title')}'. Error: {error}. Defaulting to current datetime."
                    )

            source_entity_id = event_data.get("source", {}).get("id", 0)
            source_entity_type = event_data.get("source", {}).get("type", "document")
            source_entity = None
            if source_entity_type == "document":
                source_entity = TimelineEvent.SourceEntity.UPLOADED_FILE
            elif source_entity_type == "email":
                source_entity = TimelineEvent.SourceEntity.PARSED_EMAIL
            elif source_entity_type == "attachment":
                source_entity = TimelineEvent.SourceEntity.PARSED_EMAIL_ATTACHMENT

            timeline_event = TimelineEvent(
                title=event_data.get("title", ""),
                description=event_data.get("description", ""),
                event_date=event_date,
                place=event_data.get("place", ""),
                data=event_data,
                timeline=self.timeline,
                source_entity=source_entity,
                source_entity_id=source_entity_id,
            )

            try:
                timeline_event.full_clean()
                if not dry_run:
                    timeline_event.save()

                saved_events.append(timeline_event)
            except ValidationError as e:
                logger.error(
                    f"Validation error for event '{timeline_event.title}': {e}"
                )
                continue

        return saved_events

    def run(self, dry: bool = False) -> list[TimelineEvent]:
        """Main method to run the event reconstruction process for the timeline.

        Args:
            dry (bool): If True, reconstructed events will not be saved to the database.
        Returns:
            list[TimelineEvent]: A list of TimelineEvent objects created from the reconstructed event data. Not saved to the database if dry=True.
        """
        candidate_events = self._get_content()
        events_data = self._reconstruct_events(candidate_events)
        timeline_events = self._save_reconstructed_events(events_data, dry_run=dry)
        logger.debug(
            f"No. of reconstructed events: {len(timeline_events)} from LLM, {len(timeline_events)} saved to the database (dry_run={dry})"
        )
        return timeline_events
