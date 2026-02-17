from unittest.mock import Mock, patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone

from events.models import Event
from poc.models import UploadedFile


@pytest.fixture()
def uploaded_file(cases, uploaded_file_factory):
    case = cases["mahadevan_vs_gopalan"]
    uploaded_file = uploaded_file_factory.create(
        filename="document.pdf",
        file="poc/uploaded_files/document.pdf",
        case=case,
        exhibit_code="P-1",
    )
    return uploaded_file


@pytest.mark.django_db
def test_command_errors_for_missing_uploaded_file():
    with pytest.raises(CommandError, match="does not exist"):
        call_command("extract_events_from_uploaded_file", 99999)


@pytest.mark.django_db
def test_command_skips_when_in_progress(capsys, uploaded_file):
    uploaded_file.event_extraction_status = (
        UploadedFile.EventExtractionStatus.IN_PROGRESS
    )
    uploaded_file.save(update_fields=["event_extraction_status"])

    with patch(
        "events.management.commands.extract_events_from_uploaded_file.UploadedFileEventExtractor"
    ) as service_cls:
        call_command("extract_events_from_uploaded_file", uploaded_file.id)

    service_cls.assert_not_called()
    uploaded_file.refresh_from_db()
    assert (
        uploaded_file.event_extraction_status
        == UploadedFile.EventExtractionStatus.IN_PROGRESS
    )
    output = capsys.readouterr().out
    assert "already in progress" in output


@pytest.mark.django_db
def test_command_marks_failed_on_service_error(uploaded_file):
    service = Mock()
    service.extract_events.side_effect = ValueError("boom")
    with patch(
        "events.management.commands.extract_events_from_uploaded_file.UploadedFileEventExtractor",
        return_value=service,
    ):
        with pytest.raises(CommandError, match="boom"):
            call_command("extract_events_from_uploaded_file", uploaded_file.id)

    uploaded_file.refresh_from_db()
    assert (
        uploaded_file.event_extraction_status
        == UploadedFile.EventExtractionStatus.FAILED
    )
    assert uploaded_file.event_extraction_error_message == "boom"


@pytest.mark.django_db
def test_command_marks_completed_when_no_events(capsys, uploaded_file):
    service = Mock()
    service.extract_events.return_value = []
    with patch(
        "events.management.commands.extract_events_from_uploaded_file.UploadedFileEventExtractor",
        return_value=service,
    ):
        call_command("extract_events_from_uploaded_file", uploaded_file.id)

    uploaded_file.refresh_from_db()
    assert (
        uploaded_file.event_extraction_status
        == UploadedFile.EventExtractionStatus.EXTRACTED
    )
    output = capsys.readouterr().out
    assert "No NEW events" in output


@pytest.mark.django_db
def test_command_saves_valid_events_and_reports_validation_errors(
    capsys, uploaded_file
):
    event_date = timezone.now()

    valid_event = Event(
        title="Event 1",
        description="Desc",
        event_date=event_date,
        place="",
        data={"title": "Event 1"},
        source_entity=Event.SourceEntity.UPLOADED_FILE,
        source_entity_id=uploaded_file.id,
    )
    invalid_event = Event(
        title="",
        description="Desc",
        event_date=event_date,
        place="",
        data={"title": ""},
        source_entity=Event.SourceEntity.UPLOADED_FILE,
        source_entity_id=uploaded_file.id,
    )

    service = Mock()
    service.extract_events.return_value = [valid_event, invalid_event]
    with patch(
        "events.management.commands.extract_events_from_uploaded_file.UploadedFileEventExtractor",
        return_value=service,
    ):
        call_command("extract_events_from_uploaded_file", uploaded_file.id)

    uploaded_file.refresh_from_db()
    assert (
        uploaded_file.event_extraction_status
        == UploadedFile.EventExtractionStatus.EXTRACTED
    )
    assert Event.objects.count() == 1
    saved_event = Event.objects.first()
    assert saved_event.case == uploaded_file.case

    output = capsys.readouterr().out
    assert "Validation error for event" in output
    assert "1 out of 2 events" in output
