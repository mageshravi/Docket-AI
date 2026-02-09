from django.dispatch import receiver

from poc.signals import (
    parsed_email_attachment_created,
    parsed_email_created,
    uploaded_file_created,
)

from .tasks import (
    extract_events_from_parsed_email,
    extract_events_from_parsed_email_attachment,
    extract_events_from_uploaded_file,
)


@receiver(uploaded_file_created)
def handle_uploaded_file_created(sender, instance, **kwargs):
    """Extract events when a new uploaded file is created."""
    extract_events_from_uploaded_file.delay(instance.id)


@receiver(parsed_email_created)
def handle_parsed_email_created(sender, instance, **kwargs):
    """Extract events when a new parsed email is created."""
    extract_events_from_parsed_email.delay(instance.id)


@receiver(parsed_email_attachment_created)
def handle_parsed_email_attachment_created(sender, instance, **kwargs):
    """Extract events when a new parsed email attachment is created."""
    extract_events_from_parsed_email_attachment.delay(instance.id)
