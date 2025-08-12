from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import ParsedEmail, ParsedEmailAttachment, UploadedFile
from .tasks import embed_email, embed_email_attachment, process_uploaded_file


@receiver(post_save, sender=UploadedFile)
def handle_uploaded_file_save(sender, instance, created, **kwargs):
    if created:
        process_uploaded_file.delay(instance.id)


@receiver(post_save, sender=ParsedEmail)
def handle_parsed_email_save(sender, instance, created, **kwargs):
    if created:
        embed_email.delay(instance.id)


@receiver(post_save, sender=ParsedEmailAttachment)
def handle_parsed_email_attachment_save(sender, instance, created, **kwargs):
    if created:
        embed_email_attachment.delay(instance.id)
