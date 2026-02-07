from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from events.services import EventExtractorService
from poc.models import ParsedEmailAttachment


class Command(BaseCommand):
    help = "Extract events from parsed email attachments and save them to the database."

    def add_arguments(self, parser):
        parser.add_argument(
            "attachment_id",
            type=int,
            help="ID of the parsed email attachment to extract events from.",
        )

    def handle(self, *args, **options):
        attachment_id = options["attachment_id"]

        try:
            attachment = ParsedEmailAttachment.objects.get(id=attachment_id)
        except ParsedEmailAttachment.DoesNotExist:
            raise CommandError(
                f"ParsedEmailAttachment with ID {attachment_id} does not exist."
            )

        self.stdout.write(
            f"Extracting events from parsed email attachment ID {attachment_id}."
        )

        service = EventExtractorService()
        try:
            events = service.extract_from_parsed_email_attachment(
                attachment_id=attachment.id
            )
        except (ValueError, RuntimeError) as err:
            raise CommandError(str(err))

        if not events:
            self.stdout.write(
                self.style.WARNING(
                    f"No NEW events were extracted from attachment ID {attachment_id}."
                )
            )
            return

        success_count = 0
        for event in events:
            try:
                event.full_clean()  # Validate the event data before saving
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

        if len(events) == success_count:
            self.stdout.write(
                self.style.SUCCESS(
                    f"All {len(events)} events extracted and saved successfully."
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    f"Extracted {len(events)} events, but only {success_count} were saved successfully due to validation errors."
                )
            )
