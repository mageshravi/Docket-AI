from django.db.models.signals import post_save
from django.dispatch import Signal, receiver

from .models import ParsedEmail, ParsedEmailAttachment, UploadedFile
from .tasks import embed_email, embed_email_attachment, process_uploaded_file

# Custom signals for cross-app communication
uploaded_file_created = Signal()
parsed_email_created = Signal()
parsed_email_attachment_created = Signal()


@receiver(post_save, sender=UploadedFile)
def handle_uploaded_file_save(sender, instance, created, **kwargs):
    if not created:
        return

    process_uploaded_file.delay(instance.id)
    # useful for listeners in other apps that want to trigger additional processing when a file is uploaded
    uploaded_file_created.send(sender=sender, instance=instance)


@receiver(post_save, sender=ParsedEmail)
def handle_parsed_email_save(sender, instance, created, **kwargs):
    if not created:
        return

    embed_email.delay(instance.id)
    # useful for listeners in other apps that want to trigger additional processing when a parsed email is created
    parsed_email_created.send(sender=sender, instance=instance)


@receiver(post_save, sender=ParsedEmailAttachment)
def handle_parsed_email_attachment_save(sender, instance, created, **kwargs):
    if not created:
        return

    embed_email_attachment.delay(instance.id)
    # useful for listeners in other apps that want to trigger additional processing when a parsed email attachment is created
    parsed_email_attachment_created.send(sender=sender, instance=instance)
