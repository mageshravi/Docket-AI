from celery import shared_task
from django.core.management import call_command


@shared_task
def extract_events_from_uploaded_file(uploaded_file_id: int):
    """
    Extract events from the uploaded file.
    This task is called when a file is uploaded.
    """
    call_command("extract_events_from_uploaded_file", uploaded_file_id)


@shared_task
def extract_events_from_parsed_email(parsed_email_id: int):
    """
    Extract events from the parsed email.
    This task is called when a parsed email is saved to database.
    """
    call_command("extract_events_from_parsed_email", parsed_email_id)


@shared_task
def extract_events_from_parsed_email_attachment(parsed_email_attachment_id: int):
    """
    Extract events from the parsed email attachment.
    This task is called when a parsed email attachment is saved to database.
    """
    call_command(
        "extract_events_from_parsed_email_attachment", parsed_email_attachment_id
    )
