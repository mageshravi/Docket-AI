from django.core.management.base import BaseCommand

from poc.models import ParsedEmailAttachment, ParsedEmailAttachmentEmbedding
from poc.utils import (
    create_chunks_for_vector_embedding,
    create_vector_embedding,
    extract_text_from_csv,
    extract_text_from_docx,
    extract_text_from_pdf,
    extract_text_from_pptx,
    extract_text_from_txt,
    extract_text_from_xlsx,
)


class Command(BaseCommand):
    help = "Vectorize email attachments and store embeddings"

    def add_arguments(self, parser):
        parser.add_argument(
            "attachment_id",
            type=int,
            help="ID of the parsed email attachment to vectorize",
        )

        parser.add_argument(
            "--force",
            action="store_true",
            help="Force vectorization even if the attachment is already processed",
        )

    def handle(self, *args, **kwargs):
        attachment_id = kwargs["attachment_id"]
        force = kwargs.get("force", False)

        try:
            attachment = ParsedEmailAttachment.objects.get(id=attachment_id)

            self._validate_file_size(attachment)

            if not self._validate_status(attachment, force):
                self._force_cleanup(attachment)

            if attachment.filename.endswith(".xlsx"):
                # Handle XLSX files with a specific method (different from others)
                self._handle_xlsx_attachment(attachment)
            elif attachment.filename.endswith(".pdf"):
                self._chunk_and_embed_with_rolling_buffer(
                    attachment, extract_function=extract_text_from_pdf
                )
            elif attachment.filename.endswith(".docx"):
                self._chunk_and_embed_with_rolling_buffer(
                    attachment, extract_function=extract_text_from_docx
                )
            elif attachment.filename.endswith(".pptx"):
                self._chunk_and_embed_with_rolling_buffer(
                    attachment, extract_function=extract_text_from_pptx
                )
            elif attachment.filename.endswith(".txt"):
                self._chunk_and_embed_with_rolling_buffer(
                    attachment, extract_function=extract_text_from_txt
                )
            elif attachment.filename.endswith(".csv"):
                self._chunk_and_embed_with_rolling_buffer(
                    attachment, extract_function=extract_text_from_csv
                )
            else:
                self.stderr.write(
                    self.style.WARNING(
                        f"Unsupported file type for attachment {attachment.filename}. Skipping."
                    )
                )
                attachment.mark_as_failed("Unsupported file type.")
                return
        except ParsedEmailAttachment.DoesNotExist:
            self.stderr.write(
                self.style.ERROR(
                    f"Parsed email attachment with ID {attachment_id} does not exist."
                )
            )
        except (ValueError, RuntimeError) as err:
            if attachment:
                attachment.mark_as_failed(str(err))

            self.stderr.write(self.style.ERROR(str(err)))
        except Exception as err:
            if attachment:
                attachment.mark_as_failed(str(err))

            self.stderr.write(
                self.style.ERROR(
                    f"Failed to vectorize attachment {attachment_id}: {err}"
                )
            )

    def _validate_status(
        self, attachment: ParsedEmailAttachment, force: bool = False
    ) -> bool:
        """
        Validate the status of the attachment before processing.

        Args:
            attachment (ParsedEmailAttachment): The attachment to validate.
            force (bool, optional): Whether to force process. Defaults to False.

        Raises:
            RuntimeError: If the attachment is already being processed.
            RuntimeError: If the attachment has already been processed and force is not set.

        Returns:
            bool: True if the attachment is valid for processing, False otherwise.
        """
        if (
            attachment.embedding_status
            == ParsedEmailAttachment.EmbeddingStatus.PROCESSING
        ):
            raise RuntimeError(
                f"Attachment with ID {attachment.id} is already being processed."
            )

        if attachment.embedding_status in [
            ParsedEmailAttachment.EmbeddingStatus.COMPLETED,
            ParsedEmailAttachment.EmbeddingStatus.FAILED,
        ]:
            if not force:
                raise RuntimeError(
                    f"Attachment with ID {attachment.id} has already been processed. Use --force to retry."
                )

            return False

        return True

    def _force_cleanup(self, attachment: ParsedEmailAttachment):
        """Force cleanup of existing embeddings for the attachment."""
        ParsedEmailAttachmentEmbedding.objects.filter(
            parsed_email_attachment=attachment
        ).delete()
        self.stdout.write(
            f"Force cleanup: Deleted existing embeddings for attachment {attachment.id}."
        )

    def _validate_file_size(self, attachment: ParsedEmailAttachment):
        """
        Validate the file size of the attachment.

        Raises:
            ValueError: If the file size exceeds the 25MB limit.
        """
        if attachment.file.size > 25 * 1024 * 1024:
            raise ValueError(
                f"Attachment {attachment.id} exceeds the size limit of 25MB."
            )

    def _chunk_and_embed_with_rolling_buffer(
        self,
        attachment: ParsedEmailAttachment,
        extract_function,
        buffer_size=7900,
        buffer_overlap=100,
    ):
        """
        Handle attachments by extracting text, chunking it, and creating embeddings.

        Args:
            attachment (ParsedEmailAttachment): The attachment to process.
            extract_function (callable): Function to extract text from the attachment.
            buffer_size (int): Size of the buffer to accumulate text before processing.
            buffer_overlap (int): Number of characters to overlap between buffer chunks.
        """
        chunk_idx = 0
        rolling_buffer = ""

        attachment.mark_as_processing()
        self.stdout.write(f"Processing attachment {attachment.id} for vectorization...")

        # Extract text from the attachment
        for content in extract_function(attachment.file.path):
            rolling_buffer += content

            # Process buffer when it exceeds the threshold
            while len(rolling_buffer) >= (buffer_size + buffer_overlap):
                # Extract buffer content up to the threshold
                buffer_to_process = rolling_buffer[: buffer_size + buffer_overlap]
                rolling_buffer = rolling_buffer[buffer_size:]

                # Create chunks and embeddings for the buffer
                chunks = create_chunks_for_vector_embedding(buffer_to_process)
                embeddings = create_vector_embedding(chunks)
                for embedding in embeddings:
                    ParsedEmailAttachmentEmbedding.objects.create(
                        parsed_email_attachment=attachment,
                        chunk_index=chunk_idx,
                        chunk=embedding["text"],
                        embedding=embedding["embedding"],
                    )
                    chunk_idx += 1

        # Process any remaining content in the buffer
        if rolling_buffer.strip():
            chunks = create_chunks_for_vector_embedding(rolling_buffer)
            embeddings = create_vector_embedding(chunks)
            for embedding in embeddings:
                ParsedEmailAttachmentEmbedding.objects.create(
                    parsed_email_attachment=attachment,
                    chunk_index=chunk_idx,
                    chunk=embedding["text"],
                    embedding=embedding["embedding"],
                )
                chunk_idx += 1

        attachment.mark_as_completed()

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully vectorized attachment {attachment.id}. Created {chunk_idx} embeddings."
            )
        )

    def _handle_xlsx_attachment(self, attachment: ParsedEmailAttachment):
        """
        Handle XLSX attachments by extracting text and creating embeddings.

        Args:
            attachment (ParsedEmailAttachment): The attachment to process.
        """
        chunk_idx = 0
        rolling_buffer = ""
        BUFFER_SIZE = 8000  # Accumulate 8000 characters before processing

        attachment.mark_as_processing()

        self.stdout.write(
            f"Processing XLSX attachment {attachment.id} for vectorization..."
        )

        for sheet_content in extract_text_from_xlsx(attachment.file.path):
            rolling_buffer += sheet_content

            # Process buffer when it exceeds the threshold
            while len(rolling_buffer) > BUFFER_SIZE:
                # Extract buffer content to the nearest newline character after BUFFER_SIZE
                if len(rolling_buffer) > BUFFER_SIZE:
                    last_newline = rolling_buffer.rfind("\n", 0, BUFFER_SIZE)
                    if last_newline != -1:
                        buffer_to_process = rolling_buffer[: last_newline + 1]
                    else:
                        buffer_to_process = rolling_buffer[:BUFFER_SIZE]
                else:
                    buffer_to_process = rolling_buffer

                # Remove processed content from the rolling buffer
                if last_newline != -1:
                    rolling_buffer = rolling_buffer[last_newline + 1 :]
                else:
                    rolling_buffer = rolling_buffer[BUFFER_SIZE:]

                # Create chunks and embeddings for the buffer
                chunks = create_chunks_for_vector_embedding(buffer_to_process)
                embeddings = create_vector_embedding(chunks)
                for embedding in embeddings:
                    ParsedEmailAttachmentEmbedding.objects.create(
                        parsed_email_attachment=attachment,
                        chunk_index=chunk_idx,
                        chunk=embedding["text"],
                        embedding=embedding["embedding"],
                    )
                    chunk_idx += 1

        # Process any remaining content in the buffer
        if rolling_buffer.strip():
            chunks = create_chunks_for_vector_embedding(rolling_buffer)
            embeddings = create_vector_embedding(chunks)
            for embedding in embeddings:
                ParsedEmailAttachmentEmbedding.objects.create(
                    parsed_email_attachment=attachment,
                    chunk_index=chunk_idx,
                    chunk=embedding["text"],
                    embedding=embedding["embedding"],
                )
                chunk_idx += 1

        attachment.mark_as_completed()

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully vectorized XLSX attachment {attachment.id}. Created {chunk_idx} embeddings."
            )
        )
