from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from events.services import UploadedFileEventExtractor
from poc.models import UploadedFile


class Command(BaseCommand):
    help = "Extract events from an uploaded file and save them to the database."

    def add_arguments(self, parser):
        parser.add_argument(
            "uploaded_file_id",
            type=int,
            help="ID of the uploaded file to extract events from.",
        )

    def handle(self, *args, **options):
        uploaded_file_id = options["uploaded_file_id"]

        try:
            uploaded_file = UploadedFile.objects.get(id=uploaded_file_id)
        except UploadedFile.DoesNotExist:
            raise CommandError(
                f"UploadedFile with ID {uploaded_file_id} does not exist."
            )

        if (
            uploaded_file.event_extraction_status
            == UploadedFile.EventExtractionStatus.IN_PROGRESS
        ):
            self.stdout.write(
                self.style.WARNING(
                    f"Event extraction is already in progress for uploaded file ID {uploaded_file_id}."
                )
            )
            return

        uploaded_file.mark_event_extraction_in_progress()

        self.stdout.write(
            f"Extracting events from uploaded file ID {uploaded_file_id}."
        )

        service = UploadedFileEventExtractor()
        try:
            events = service.extract_events(source_entity_id=uploaded_file.id)
        except (ValueError, RuntimeError) as err:
            uploaded_file.mark_event_extraction_failed(error_message=str(err))
            raise CommandError(str(err))

        if not events:
            uploaded_file.mark_event_extraction_completed()
            self.stdout.write(
                self.style.WARNING(
                    f"No NEW events were extracted from uploaded file ID {uploaded_file_id}."
                )
            )
            return

        success_count = 0
        for event in events:
            try:
                event.full_clean()
                event.save()
                self.stdout.write(f"New event saved: {event}")
                success_count += 1
            except ValidationError as err:
                self.stdout.write(
                    self.style.ERROR(
                        f"Validation error for event '{event.title}': {err}"
                    )
                )

        uploaded_file.mark_event_extraction_completed()

        if success_count == len(events):
            self.stdout.write(
                self.style.SUCCESS(
                    f"All {len(events)} extracted and saved successfully."
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    f"{success_count} out of {len(events)} events extracted were saved successfully."
                )
            )
