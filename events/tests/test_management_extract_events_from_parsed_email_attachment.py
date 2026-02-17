from unittest.mock import Mock, patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone

from events.models import Event
from poc.models import ParsedEmailAttachment


@pytest.fixture()
def parsed_email_attachment(
    cases,
    uploaded_file_factory,
    parsed_email_factory,
    parsed_email_attachment_factory,
):
    case = cases["mahadevan_vs_gopalan"]
    uploaded_file = uploaded_file_factory.create(
        filename="email.txt",
        file="poc/uploaded_files/email.txt",
        case=case,
        exhibit_code="P-1",
    )
    email = parsed_email_factory.create(
        uploaded_file=uploaded_file,
        sent_on=timezone.now(),
        sender="sender@example.com",
        to_recipients="to@example.com",
        cc_recipients="",
        subject="Subject",
        body="Body",
        cleaned_body="Cleaned",
    )
    attachment = parsed_email_attachment_factory.create(
        parsed_email=email,
        file="poc/uploaded_files/attachments/a.txt",
        filename="a.txt",
        content_type="text/plain",
        size=5,
    )
    return attachment


@pytest.mark.django_db
def test_command_errors_for_missing_attachment():
    with pytest.raises(CommandError, match="does not exist"):
        call_command("extract_events_from_parsed_email_attachment", 99999)


@pytest.mark.django_db
def test_command_skips_when_in_progress(capsys, parsed_email_attachment):
    attachment = parsed_email_attachment
    attachment.event_extraction_status = (
        ParsedEmailAttachment.EventExtractionStatus.IN_PROGRESS
    )
    attachment.save(update_fields=["event_extraction_status"])

    with patch(
        "events.management.commands.extract_events_from_parsed_email_attachment.EmailAttachmentEventExtractor"
    ) as service_cls:
        call_command("extract_events_from_parsed_email_attachment", attachment.id)

    service_cls.assert_not_called()
    attachment.refresh_from_db()
    assert (
        attachment.event_extraction_status
        == ParsedEmailAttachment.EventExtractionStatus.IN_PROGRESS
    )
    output = capsys.readouterr().out
    assert "already in progress" in output


@pytest.mark.django_db
def test_command_marks_failed_on_service_error(parsed_email_attachment):
    attachment = parsed_email_attachment

    service = Mock()
    service.extract_events.side_effect = ValueError("boom")
    with patch(
        "events.management.commands.extract_events_from_parsed_email_attachment.EmailAttachmentEventExtractor",
        return_value=service,
    ):
        with pytest.raises(CommandError, match="boom"):
            call_command("extract_events_from_parsed_email_attachment", attachment.id)

    attachment.refresh_from_db()
    assert (
        attachment.event_extraction_status
        == ParsedEmailAttachment.EventExtractionStatus.FAILED
    )
    assert attachment.event_extraction_error_message == "boom"


@pytest.mark.django_db
def test_command_marks_completed_when_no_events(capsys, parsed_email_attachment):
    attachment = parsed_email_attachment

    service = Mock()
    service.extract_events.return_value = []
    with patch(
        "events.management.commands.extract_events_from_parsed_email_attachment.EmailAttachmentEventExtractor",
        return_value=service,
    ):
        call_command("extract_events_from_parsed_email_attachment", attachment.id)

    attachment.refresh_from_db()
    assert (
        attachment.event_extraction_status
        == ParsedEmailAttachment.EventExtractionStatus.EXTRACTED
    )
    output = capsys.readouterr().out
    assert "No NEW events" in output


@pytest.mark.django_db
def test_command_saves_valid_events_and_reports_validation_errors(
    capsys, parsed_email_attachment
):
    attachment = parsed_email_attachment
    event_date = timezone.now()

    valid_event = Event(
        title="Event 1",
        description="Desc",
        event_date=event_date,
        place="",
        data={"title": "Event 1"},
        source_entity=Event.SourceEntity.PARSED_EMAIL_ATTACHMENT,
        source_entity_id=attachment.id,
    )
    invalid_event = Event(
        title="",
        description="Desc",
        event_date=event_date,
        place="",
        data={"title": ""},
        source_entity=Event.SourceEntity.PARSED_EMAIL_ATTACHMENT,
        source_entity_id=attachment.id,
    )

    service = Mock()
    service.extract_events.return_value = [valid_event, invalid_event]
    with patch(
        "events.management.commands.extract_events_from_parsed_email_attachment.EmailAttachmentEventExtractor",
        return_value=service,
    ):
        call_command("extract_events_from_parsed_email_attachment", attachment.id)

    attachment.refresh_from_db()
    assert (
        attachment.event_extraction_status
        == ParsedEmailAttachment.EventExtractionStatus.EXTRACTED
    )
    assert Event.objects.count() == 1
    saved_event = Event.objects.first()
    assert saved_event.case == attachment.parsed_email.uploaded_file.case

    output = capsys.readouterr().out
    assert "Validation error for event" in output
    assert "1 out of 2 events" in output
