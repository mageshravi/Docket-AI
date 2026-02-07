import json
import logging

from django.conf import settings
from django.db.models import QuerySet
from django.utils import timezone
from openai import OpenAI, OpenAIError

from poc.models import ParsedEmailAttachment
from poc.utils import (
    extract_text_from_csv,
    extract_text_from_docx,
    extract_text_from_pdf,
    extract_text_from_pptx,
    extract_text_from_txt,
    extract_text_from_xlsx,
)

from .models import Event

logger = logging.getLogger(__name__)


class EventExtractorService:
    """Service for extracting events from a given input."""

    def __init__(self, prompt_filepath: str = None):
        self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)

        if prompt_filepath is None:
            prompt_filepath = settings.BASE_DIR.joinpath(
                "events", "docs", "prompts", "event_extraction_prompt.md"
            )

        with open(prompt_filepath, "r") as file:
            self.prompt_instructions = file.read()

    def extract_from_parsed_email_attachment(self, attachment_id: int) -> list[Event]:
        """Extracts events from a parsed email attachment.

        Args:
            attachment_id (int): The ID of the parsed email attachment to extract events from.

        Returns:
            list[Event]: A list of extracted Event objects (NOT saved to the database).

        Raises:
            ValueError: If the parsed email attachment with the given ID does not exist.
        """
        try:
            attachment = ParsedEmailAttachment.objects.get(id=attachment_id)
        except ParsedEmailAttachment.DoesNotExist:
            raise ValueError(
                f"ParsedEmailAttachment with ID {attachment_id} does not exist."
            )

        content = self._get_content_from_attachment(attachment)

        events = []

        _events = self._parse_events_from_content(content)
        for _event in _events:
            # default to now if event_date is missing or invalid
            event_date = timezone.datetime.now()
            if event_date_str := _event.get("event_date"):
                try:
                    event_date = timezone.datetime.fromisoformat(event_date_str)
                    if event_date.tzinfo is None:
                        # convert to local timezone
                        event_date = timezone.make_aware(event_date)
                except ValueError as error:
                    logger.info(
                        f"Failed to parse event_date '{event_date_str}' for event '{_event.get('title')}'. Error: {error}. Defaulting to current datetime."
                    )

            event = Event(
                title=_event.get("title"),
                description=_event.get("description"),
                event_date=event_date,
                place=_event.get("place", ""),
                data=_event,
                source_entity=Event.SourceEntity.PARSED_EMAIL_ATTACHMENT,
                source_entity_id=attachment.id,
            )
            events.append(event)

        return events

    def _get_content_from_attachment(self, attachment: ParsedEmailAttachment) -> str:
        attachment_names = ", ".join(
            _attachment.filename
            for _attachment in ParsedEmailAttachment.objects.filter(
                parsed_email=attachment.parsed_email
            )
        )
        content = (
            "[Email Attachment]\n"
            "Email:\n"
            f"\tSubject: {attachment.parsed_email.subject}\n"
            f"\tFrom: {attachment.parsed_email.sender}\n"
            f"\tTo: {attachment.parsed_email.to_recipients}\n"
            f"\tCc: {attachment.parsed_email.cc_recipients}\n"
            f"\tAttachments: {attachment_names}\n"
            f"\tSent On: {attachment.parsed_email.sent_on}\n"
            f"Filename: {attachment.filename}\n"
            f"Content Type: {attachment.content_type}\n"
            f"Content:\n"
        )

        extraction_function = None

        if attachment.content_type == "text/plain":
            extraction_function = extract_text_from_txt
        elif attachment.content_type == "text/csv":
            extraction_function = extract_text_from_csv
        elif attachment.content_type in [
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.ms-excel",
        ]:
            extraction_function = extract_text_from_xlsx
        elif attachment.content_type in [
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/msword",
        ]:
            extraction_function = extract_text_from_docx
        elif attachment.content_type in [
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "application/vnd.ms-powerpoint",
        ]:
            extraction_function = extract_text_from_pptx
        elif attachment.content_type == "application/pdf":
            extraction_function = extract_text_from_pdf
        else:
            logger.warning(
                f"Unsupported content type '{attachment.content_type}' for attachment ID {attachment.id}. Skipping content extraction."
            )

        if extraction_function:
            for chunk in extraction_function(attachment.file):
                content += chunk

        # Include existing extracted events from this attachment in the content for context, if any exist
        existing_events = self._get_existing_events(attachment)
        if existing_events.exists():
            logger.info(
                f"Found {existing_events.count()} existing events for attachment ID {attachment.id}. Including existing event data in the content for context."
            )
            content += "\nExisting Extracted Events:\n"
            for event in existing_events:
                content += json.dumps(event.data, indent=2) + "\n"

        return content

    def _get_existing_events(
        self, attachment: ParsedEmailAttachment
    ) -> QuerySet[Event]:
        """Retrieves existing events from the database that were previously extracted from the given parsed email attachment.

        Args:
            attachment (ParsedEmailAttachment): The parsed email attachment to check for existing events.
        Returns:
            QuerySet[Event]: A queryset of existing Event objects that were extracted from the given parsed email attachment.
        """
        return Event.objects.filter(
            source_entity=Event.SourceEntity.PARSED_EMAIL_ATTACHMENT,
            source_entity_id=attachment.id,
        )

    def _parse_events_from_content(self, content: str) -> list[dict]:
        """Parses the events from the given file content using LLM (OpenAI).

        Args:
            content (str): the extracted file content

        Returns:
            list[dict]: List of extracted events
        """
        try:
            response = self.openai_client.responses.create(
                model="gpt-4o",
                input=[
                    {"role": "system", "content": self.prompt_instructions},
                    {"role": "user", "content": content},
                ],
            )

            if response.output_text:
                return json.loads(response.output_text)

            return []
        except OpenAIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise RuntimeError(
                "Failed to parse events from content due to an OpenAI API error."
            )
        except json.JSONDecodeError as e:
            logger.error(
                f"JSON decoding error: {e}. Response text: {response.output_text}"
            )
            raise ValueError(
                "Failed to parse events from content due to invalid JSON format in the LLM response."
            )
