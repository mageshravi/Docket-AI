from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from events.services import EmailEventExtractor
from poc.models import ParsedEmail


class Command(BaseCommand):
    help = "Extract events from parsed emails and save them to the database."

    def add_arguments(self, parser):
        parser.add_argument(
            "email_id",
            type=int,
            help="ID of the parsed email to extract events from.",
        )

    def handle(self, *args, **options):
        email_id = options["email_id"]

        try:
            email = ParsedEmail.objects.select_related("uploaded_file__case").get(
                id=email_id
            )
        except ParsedEmail.DoesNotExist:
            raise CommandError(f"ParsedEmail with ID {email_id} does not exist.")

        if (
            email.event_extraction_status
            == ParsedEmail.EventExtractionStatus.IN_PROGRESS
        ):
            self.stdout.write(
                self.style.WARNING(
                    f"Event extraction is already in progress for email ID {email_id}."
                )
            )
            return

        email.mark_event_extraction_in_progress()

        self.stdout.write(f"Extracting events from parsed email ID {email_id}.")

        service = EmailEventExtractor()
        try:
            events = service.extract_events(source_entity_id=email.id)
        except (ValueError, RuntimeError) as err:
            email.mark_event_extraction_failed(error_message=str(err))
            raise CommandError(str(err))

        if not events:
            email.mark_event_extraction_completed()
            self.stdout.write(
                self.style.WARNING(
                    f"No NEW events were extracted from email ID {email_id}."
                )
            )
            return

        success_count = 0
        for event in events:
            try:
                event.case = email.uploaded_file.case
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
                self.stdout.write(f"Event data: {event.data}")

        email.mark_event_extraction_completed()

        if len(events) == success_count:
            self.stdout.write(
                self.style.SUCCESS(
                    f"All {len(events)} events extracted from email ID {email_id} were saved successfully."
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    f"{success_count} out of {len(events)} events extracted from email ID {email_id} were saved successfully."
                )
            )
