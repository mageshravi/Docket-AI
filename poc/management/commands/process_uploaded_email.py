import base64

import mailparser
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand
from email_reply_parser import EmailReplyParser

from poc.models import ParsedEmail, ParsedEmailAttachment, UploadedFile


class Command(BaseCommand):
    help = "Process uploaded email files"

    def add_arguments(self, parser):
        parser.add_argument(
            "file_id", type=int, help="ID of the uploaded-file to process"
        )

        parser.add_argument(
            "--force",
            action="store_true",
            help="Force processing of the file even if it is not in PENDING status",
        )

    def handle(self, *args, **kwargs):
        file_id = kwargs["file_id"]

        try:
            uploaded_file = UploadedFile.objects.get(id=file_id)
        except UploadedFile.DoesNotExist:
            self.stderr.write(
                self.style.ERROR(f"Uploaded file with ID {file_id} does not exist.")
            )
            return

        # check if the file is valid EML file
        if not uploaded_file.file.name.endswith(".eml"):
            self.stderr.write(
                self.style.ERROR(f"File with ID {file_id} is not a valid EML file.")
            )
            return

        if uploaded_file.status != UploadedFile.Status.PENDING and not kwargs["force"]:
            self.stderr.write(
                self.style.ERROR(
                    f"File with ID {file_id} is not in PENDING status. Use --force to process it anyway."
                )
            )
            return

        # Mark the file as processing
        uploaded_file.mark_as_processing()

        try:
            email, cleaned_body = self._parse_email(uploaded_file)

            from_ = self._get_email_display_name(email.from_[0])
            to_ = ", ".join(self._get_email_display_name(addr) for addr in email.to)
            cc_ = (
                ", ".join(self._get_email_display_name(addr) for addr in email.cc)
                if email.cc
                else None
            )

            parsed_email, created = ParsedEmail.objects.update_or_create(
                defaults={
                    "sent_on": email.date,
                    "sender": from_,
                    "to_recipients": to_,
                    "cc_recipients": cc_,
                    "subject": email.subject,
                    "body": email.body,
                    "cleaned_body": cleaned_body,
                    "ai_summary": "",
                },
                uploaded_file=uploaded_file,
            )

            if not created:
                self.stdout.write(
                    self.style.NOTICE(
                        f"Updated existing ParsedEmail for file ID {file_id}."
                    )
                )

                attachments = parsed_email.parsed_attachments.all()
                if attachments.exists():
                    for attachment in attachments:
                        # delete the file from storage
                        attachment.file.delete(save=False)

                    # delete the existing records
                    attachments.delete()
                    self.stdout.write(
                        self.style.NOTICE(
                            f"Deleted existing attachments for ParsedEmail ID {parsed_email.id}."
                        )
                    )

            parsed_attachments = []
            for attachment in email.attachments:
                # create file from the attachment payload
                attachment_file = self._save_attachment(attachment)
                # create ParsedEmailAttachment instance and link it to the parsed email
                parsed_email_attachment = ParsedEmailAttachment.objects.create(
                    parsed_email=parsed_email,
                    file=attachment_file,
                    filename=attachment["filename"],
                    content_type=attachment["mail_content_type"],
                    size=len(attachment["payload"]),
                    ai_summary="",
                )
                parsed_attachments.append(parsed_email_attachment)

            # Mark the file as completed
            uploaded_file.mark_as_completed()

            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully processed file # {file_id}. Parsed Email # {parsed_email.id} with {len(parsed_attachments)} attachments."
                )
            )

        except FileNotFoundError:
            self.stderr.write(
                self.style.ERROR(
                    f"File {uploaded_file.file.name} not found in storage."
                )
            )
            uploaded_file.mark_as_failed("File not found.")
            return
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error processing file: {e}"))
            uploaded_file.mark_as_failed(str(e))
            raise e

    def _parse_email(self, uploaded_file):
        email = mailparser.parse_from_file(uploaded_file.file.path)
        cleaned_body = EmailReplyParser.parse_reply(email.body)

        return (email, cleaned_body)

    def _get_email_display_name(self, email: tuple) -> str:
        """Returns a unified display name for the email address.

        For example, for the input ('John Doe', '<john.doe@example.com>'), it should return 'John Doe <john.doe@example.com>'.
        """
        if len(email) > 1:
            if email[0] == email[1]:
                return email[1]

            return f"{email[0]} <{email[1]}>"

        return email[0]

    def _save_attachment(self, attachment):
        """Saves the attachment to the file system and returns the file path."""
        # Create a ContentFile from the attachment payload
        decoded_payload = base64.b64decode(attachment["payload"])
        content_file = ContentFile(decoded_payload, name=attachment["filename"])
        file_path = f"poc/uploaded_files/attachments/{attachment['filename']}"

        # Save the file using the storage system
        return default_storage.save(file_path, content_file)
