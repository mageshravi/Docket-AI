import json
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from events.models import Event
from events.services import (
    BaseEventExtractor,
    EmailAttachmentEventExtractor,
    EmailEventExtractor,
    UploadedFileEventExtractor,
)
from poc.models import Case, ParsedEmail, ParsedEmailAttachment, UploadedFile


class DummyExtractor(BaseEventExtractor):
    def __init__(self, source_entity=None, existing_events=None):
        self.openai_client = Mock()
        self.prompt_instructions = "prompt"
        self._source_entity = source_entity
        self._existing_events = existing_events

    def get_source_entity_type(self) -> Event.SourceEntity:
        return Event.SourceEntity.PARSED_EMAIL

    def get_source_entity(self, source_entity_id: int):
        return self._source_entity

    def get_content(self, source_entity) -> str:
        return "content"

    def get_existing_events(self, source_entity):
        return self._existing_events


@pytest.mark.django_db
def test_extract_events_includes_existing_events():
    case = Case.objects.create(title="Case A", description="Desc")
    uploaded_file = UploadedFile.objects.create(
        filename="email.txt",
        file=SimpleUploadedFile("email.txt", b"hello", content_type="text/plain"),
        case=case,
        exhibit_code="P-1",
    )
    email = ParsedEmail.objects.create(
        uploaded_file=uploaded_file,
        sent_on=timezone.now(),
        sender="sender@example.com",
        to_recipients="to@example.com",
        cc_recipients="",
        subject="Subject",
        body="Body",
        cleaned_body="Cleaned",
    )
    existing_event = Event.objects.create(
        title="Old",
        description="Old event",
        event_date=timezone.now(),
        place="",
        data={"title": "Old"},
        source_entity=Event.SourceEntity.PARSED_EMAIL,
        source_entity_id=email.id,
        case=None,
    )
    existing_events = Event.objects.filter(id=existing_event.id)

    extractor = DummyExtractor(source_entity=email, existing_events=existing_events)
    extractor.deduce_events_from_content = Mock(return_value=[])
    extractor.build_event_list = Mock(return_value=[])

    extractor.extract_events(email.id)

    content_arg = extractor.deduce_events_from_content.call_args[0][0]
    assert "Existing Extracted Events:" in content_arg
    assert json.dumps(existing_event.data, indent=2) in content_arg


def test_deduce_events_from_content_parses_list():
    """Test that the method can parse a list of events from the LLM output."""
    extractor = DummyExtractor()
    extractor.openai_client.responses.create.return_value = SimpleNamespace(
        output_text='[{"title": "Event A"}]'
    )

    result = extractor.deduce_events_from_content("content")

    assert result == [{"title": "Event A"}]


def test_deduce_events_from_content_wraps_single_dict():
    """Test that the method wraps a single event dict in a list."""
    extractor = DummyExtractor()
    extractor.openai_client.responses.create.return_value = SimpleNamespace(
        output_text='{"title": "Event A"}'
    )

    result = extractor.deduce_events_from_content("content")

    assert result == [{"title": "Event A"}]


def test_deduce_events_from_content_invalid_json_raises():
    """Test that the method raises a ValueError for invalid JSON."""
    extractor = DummyExtractor()
    extractor.openai_client.responses.create.return_value = SimpleNamespace(
        output_text="not json"
    )

    with pytest.raises(ValueError):
        extractor.deduce_events_from_content("content")


def test_build_event_list_handles_dates():
    """Test that the method can build event list and handles invalid dates."""
    extractor = DummyExtractor()
    start = timezone.datetime.now()
    events = [
        {
            "title": "Event A",
            "description": "Desc",
            "event_date": "2024-01-01T10:00:00",
            "place": "Place",
        },
        {
            "title": "Event B",
            "description": "Desc",
            "event_date": "invalid",
        },
        "bad",
    ]

    result = extractor.build_event_list(
        events, Event.SourceEntity.PARSED_EMAIL, source_entity_id=1
    )
    end = timezone.datetime.now()

    assert len(result) == 2
    assert result[0].event_date.tzinfo is not None
    assert start <= result[1].event_date <= end


@pytest.mark.django_db
def test_email_attachment_get_content_uses_extraction_function():
    case = Case.objects.create(title="Case A", description="Desc")
    uploaded_file = UploadedFile.objects.create(
        filename="email.txt",
        file=SimpleUploadedFile("email.txt", b"hello", content_type="text/plain"),
        case=case,
        exhibit_code="P-1",
    )
    email = ParsedEmail.objects.create(
        uploaded_file=uploaded_file,
        sent_on=timezone.now(),
        sender="sender@example.com",
        to_recipients="to@example.com",
        cc_recipients="",
        subject="Subject",
        body="Body",
        cleaned_body="Cleaned",
    )
    attachment = ParsedEmailAttachment.objects.create(
        parsed_email=email,
        file=SimpleUploadedFile("a.txt", b"hello", content_type="text/plain"),
        filename="a.txt",
        content_type="text/plain",
        size=5,
    )

    extractor = EmailAttachmentEventExtractor(prompt_filepath=__file__)
    with patch(
        "events.services.extract_text_from_txt", return_value=["c1", "c2"]
    ) as mock_extract:
        content = extractor.get_content(attachment)

    assert "[Email Attachment]" in content
    assert "Subject: Subject" in content
    assert "Filename: a.txt" in content
    assert "c1" in content
    assert "c2" in content
    mock_extract.assert_called_once_with(attachment.file)


@pytest.mark.django_db
def test_email_get_content_includes_email_fields():
    case = Case.objects.create(title="Case A", description="Desc")
    uploaded_file = UploadedFile.objects.create(
        filename="email.txt",
        file=SimpleUploadedFile("email.txt", b"hello", content_type="text/plain"),
        case=case,
        exhibit_code="P-1",
    )
    email = ParsedEmail.objects.create(
        uploaded_file=uploaded_file,
        sent_on=timezone.now(),
        sender="sender@example.com",
        to_recipients="to@example.com",
        cc_recipients="",
        subject="Subject",
        body="Body",
        cleaned_body="Cleaned",
    )
    ParsedEmailAttachment.objects.create(
        parsed_email=email,
        file=SimpleUploadedFile("a.txt", b"hello", content_type="text/plain"),
        filename="a.txt",
        content_type="text/plain",
        size=5,
    )

    extractor = EmailEventExtractor(prompt_filepath=__file__)
    content = extractor.get_content(email)

    assert "[Email]" in content
    assert "Subject: Subject" in content
    assert "Attachments: a.txt" in content
    assert "Cleaned" in content


@pytest.mark.django_db
def test_uploaded_file_get_content_uses_extraction_function():
    case = Case.objects.create(title="Case A", description="Desc")
    uploaded_file = UploadedFile.objects.create(
        filename="file.txt",
        file=SimpleUploadedFile("file.txt", b"hello", content_type="text/plain"),
        case=case,
        exhibit_code="P-1",
    )

    extractor = UploadedFileEventExtractor(prompt_filepath=__file__)
    with patch(
        "events.services.extract_text_from_txt", return_value=["c1", "c2"]
    ) as mock_extract:
        content = extractor.get_content(uploaded_file)

    assert "[Document]" in content
    assert "Filename: file.txt" in content
    assert "c1" in content
    assert "c2" in content
    mock_extract.assert_called_once_with(uploaded_file.file)
