from celery import shared_task
from django.core.management import call_command

from .models import UploadedFile


@shared_task
def add(x: int, y: int) -> int:
    """
    Adds two numbers.
    Dummy task for verifying Celery integration.
    """
    return x + y


@shared_task
def process_uploaded_file(uploaded_file_id: int):
    """
    Process the uploaded file based on its type.
    This task is called when a file is uploaded and needs to be processed.
    """
    try:
        uploaded_file = UploadedFile.objects.get(id=uploaded_file_id)

        if uploaded_file.file.name.endswith(".eml"):
            call_command("process_uploaded_email", uploaded_file_id)
            return

        call_command("process_uploaded_file", uploaded_file_id)
    except UploadedFile.DoesNotExist:
        print(f"UploadedFile with id {uploaded_file_id} does not exist.")


@shared_task
def embed_email(parsed_email_id: int):
    """
    Create vector embeddings for the parsed email.
    This task is called after the email has been parsed and is ready for embedding.
    """
    call_command("embed_email", parsed_email_id)


@shared_task
def embed_email_attachment(parsed_email_attachment_id: int):
    """
    Create vector embeddings for the parsed email attachment.
    This task is called after the attachment has been parsed and is ready for embedding.
    """
    call_command("embed_email_attachment", parsed_email_attachment_id)
