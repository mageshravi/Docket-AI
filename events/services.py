"""Cross-app business logic for event extraction and management."""

import json
import logging
from abc import ABC, abstractmethod

from django.conf import settings
from django.db.models import QuerySet
from django.utils import timezone
from openai import OpenAI, OpenAIError

from poc.models import ParsedEmail, ParsedEmailAttachment, UploadedFile
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


class BaseEventExtractor(ABC):
    """Abstract base class for event extractor services."""

    def __init__(self, prompt_filepath: str = None):
        self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)

        if prompt_filepath is None:
            prompt_filepath = settings.BASE_DIR.joinpath(
                "events", "docs", "prompts", "event_extraction_prompt.md"
            )

        with open(prompt_filepath, "r") as file:
            self.prompt_instructions = file.read()

    @abstractmethod
    def get_source_entity_type(self) -> Event.SourceEntity:
        """Returns the source entity type that this event extractor is designed to handle (e.g., PARSED_EMAIL_ATTACHMENT or PARSED_EMAIL).

        Returns:
            Event.SourceEntity: The source entity type for this event extractor.
        """
        pass

    @abstractmethod
    def get_source_entity(
        self, source_entity_id: int
    ) -> ParsedEmail | ParsedEmailAttachment | UploadedFile:
        """Retrieves the source entity (ParsedEmail, ParsedEmailAttachment, or UploadedFile) based on the given source entity ID.

        Args:
            source_entity_id (int): The ID of the source entity to retrieve.

        Returns:
            ParsedEmail | ParsedEmailAttachment | UploadedFile: The retrieved source entity object.

        Raises:
            ValueError: If the source entity with the given ID does not exist.
        """
        pass

    def extract_events(self, source_entity_id: int) -> list[Event]:
        """Extracts events from the given source entity ID.

        Args:
            source_entity_id (int): The ID of the source entity to extract events from.
        Returns:
            list[Event]: A list of extracted Event objects (NOT saved to the database).
        """
        source_entity = self.get_source_entity(source_entity_id)
        content = self.get_content(source_entity)
        existing_events = self.get_existing_events(source_entity)
        if existing_events.exists():
            content += "\nExisting Extracted Events:\n"
            for event in existing_events:
                content += json.dumps(event.data, indent=2) + "\n"

        events_data = self.deduce_events_from_content(content)
        return self.build_event_list(
            events_data, self.get_source_entity_type(), source_entity_id
        )

    @abstractmethod
    def get_content(
        self, source_entity: ParsedEmail | ParsedEmailAttachment | UploadedFile
    ) -> str:
        """Retrieves the content to be used for event extraction based on the source entity type.

        Args:
            source_entity: The source entity object to retrieve content from (e.g., ParsedEmail or ParsedEmailAttachment).

        Returns:
            str: The content to be used for event extraction.
        """
        pass

    @abstractmethod
    def get_existing_events(
        self, source_entity: ParsedEmail | ParsedEmailAttachment | UploadedFile
    ) -> QuerySet[Event]:
        """Retrieves existing events from the database that were previously extracted from the given source entity.

        Args:
            source_entity: The source entity object to check for existing events (e.g., ParsedEmail or ParsedEmailAttachment).

        Returns:
            QuerySet[Event]: A queryset of existing Event objects that were extracted from the given source entity.
        """
        pass

    def deduce_events_from_content(self, content: str) -> list[dict]:
        """Parses the events from the given file content using LLM (OpenAI).

        Args:
            content (str): the extracted file content

        Returns:
            list[dict]: List of extracted events (dictionary format)
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

    def build_event_list(
        self,
        events: list[dict],
        source_entity: Event.SourceEntity,
        source_entity_id: int,
    ) -> list[Event]:
        """Builds a list of Event objects from the parsed event data.

        Args:
            events (list[dict]): A list of dictionaries containing the parsed event data.
            source_entity (Event.SourceEntity): The source entity type for the events (e.g., PARSED_EMAIL_ATTACHMENT).
            source_entity_id (int): The ID of the source entity (e.g., the parsed email attachment ID) that the events are associated with.

        Returns:
            list[Event]: A list of Event objects built from the parsed event data (NOT saved to the database).
        """
        result = []
        for event_data in events:
            # default to now if event_date is missing or invalid
            event_date = timezone.datetime.now()
            if event_date_str := event_data.get("event_date"):
                try:
                    event_date = timezone.datetime.fromisoformat(event_date_str)
                    if event_date.tzinfo is None:
                        # convert to local timezone
                        event_date = timezone.make_aware(event_date)
                except ValueError as error:
                    logger.info(
                        f"Failed to parse event_date '{event_date_str}' for event '{event_data.get('title')}'. Error: {error}. Defaulting to current datetime."
                    )

            event = Event(
                title=event_data.get("title"),
                description=event_data.get("description"),
                event_date=event_date,
                place=event_data.get("place", ""),
                data=event_data,
                source_entity=source_entity,
                source_entity_id=source_entity_id,
            )
            result.append(event)

        return result


class EmailAttachmentEventExtractor(BaseEventExtractor):
    """Service for extracting events from a given input."""

    def get_source_entity_type(self) -> Event.SourceEntity:
        return Event.SourceEntity.PARSED_EMAIL_ATTACHMENT

    def get_source_entity(self, source_entity_id: int) -> ParsedEmailAttachment:
        try:
            return ParsedEmailAttachment.objects.get(id=source_entity_id)
        except ParsedEmailAttachment.DoesNotExist:
            raise ValueError(
                f"ParsedEmailAttachment with ID {source_entity_id} does not exist."
            )

    def get_content(self, source_entity: ParsedEmailAttachment) -> str:
        if not isinstance(source_entity, ParsedEmailAttachment):
            raise ValueError(
                f"Invalid source entity type: expected ParsedEmailAttachment, got {type(source_entity)}"
            )

        attachment = source_entity

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

        return content

    def get_existing_events(self, source_entity) -> QuerySet[Event]:
        if not isinstance(source_entity, ParsedEmailAttachment):
            raise ValueError(
                f"Invalid source entity type: expected ParsedEmailAttachment, got {type(source_entity)}"
            )

        attachment = source_entity

        return Event.objects.filter(
            source_entity=Event.SourceEntity.PARSED_EMAIL_ATTACHMENT,
            source_entity_id=attachment.id,
        )


# todo: test this implementation.
class EmailEventExtractor(BaseEventExtractor):
    """Service for extracting events from a given input."""

    def get_source_entity_type(self) -> Event.SourceEntity:
        return Event.SourceEntity.PARSED_EMAIL

    def get_source_entity(self, source_entity_id: int) -> ParsedEmail:
        try:
            return ParsedEmail.objects.get(id=source_entity_id)
        except ParsedEmail.DoesNotExist:
            raise ValueError(f"ParsedEmail with ID {source_entity_id} does not exist.")

    def get_content(self, source_entity: ParsedEmail) -> str:
        if not isinstance(source_entity, ParsedEmail):
            raise ValueError(
                f"Invalid source entity type: expected ParsedEmail, got {type(source_entity)}"
            )

        email = source_entity

        attachment_names = ", ".join(
            attachment.filename for attachment in email.parsed_attachments.all()
        )
        content = (
            "[Email]\n"
            f"Subject: {email.subject}\n"
            f"From: {email.sender}\n"
            f"To: {email.to_recipients}\n"
            f"Cc: {email.cc_recipients}\n"
            f"Attachments: {attachment_names}\n"
            f"Sent On: {email.sent_on}\n"
            "Content:\n"
            f"{email.cleaned_body}\n"
        )

        return content

    def get_existing_events(self, source_entity) -> QuerySet[Event]:
        if not isinstance(source_entity, ParsedEmail):
            raise ValueError(
                f"Invalid source entity type: expected ParsedEmail, got {type(source_entity)}"
            )

        email = source_entity

        return Event.objects.filter(
            source_entity=Event.SourceEntity.PARSED_EMAIL,
            source_entity_id=email.id,
        )


# todo: test this implementation
class UploadedFileEventExtractor(BaseEventExtractor):
    """Service for extracting events from a given input."""

    def get_source_entity_type(self) -> Event.SourceEntity:
        return Event.SourceEntity.UPLOADED_FILE

    def get_source_entity(self, source_entity_id: int) -> UploadedFile:
        try:
            return UploadedFile.objects.get(id=source_entity_id)
        except UploadedFile.DoesNotExist:
            raise ValueError(f"UploadedFile with ID {source_entity_id} does not exist.")

    def get_content(self, source_entity: UploadedFile) -> str:
        if not isinstance(source_entity, UploadedFile):
            raise ValueError(
                f"Invalid source entity type: expected UploadedFile, got {type(source_entity)}"
            )

        uploaded_file = source_entity

        content = (
            "[Document]\n"
            f"Filename: {uploaded_file.filename}\n"
            f"Uploaded On: {uploaded_file.created_at}\n"
            # todo: include published date if available (may require additional field in UploadedFile model and handling during file upload)
            "Content:\n"
        )

        extraction_function = None

        if uploaded_file.content_type == "text/plain":
            extraction_function = extract_text_from_txt
        elif uploaded_file.content_type == "text/csv":
            extraction_function = extract_text_from_csv
        elif uploaded_file.content_type in [
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.ms-excel",
        ]:
            extraction_function = extract_text_from_xlsx
        elif uploaded_file.content_type in [
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/msword",
        ]:
            extraction_function = extract_text_from_docx
        elif uploaded_file.content_type in [
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "application/vnd.ms-powerpoint",
        ]:
            extraction_function = extract_text_from_pptx
        elif uploaded_file.content_type == "application/pdf":
            extraction_function = extract_text_from_pdf
        else:
            logger.warning(
                f"Unsupported content type '{uploaded_file.content_type}' for uploaded file ID {uploaded_file.id}. Skipping content extraction."
            )

        if extraction_function:
            for chunk in extraction_function(uploaded_file.file):
                content += chunk

        return content

    def get_existing_events(self, source_entity) -> QuerySet[Event]:
        if not isinstance(source_entity, UploadedFile):
            raise ValueError(
                f"Invalid source entity type: expected UploadedFile, got {type(source_entity)}"
            )

        uploaded_file = source_entity

        return Event.objects.filter(
            source_entity=Event.SourceEntity.UPLOADED_FILE,
            source_entity_id=uploaded_file.id,
        )
