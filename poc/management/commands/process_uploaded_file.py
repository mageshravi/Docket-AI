from django.core.management.base import BaseCommand

from poc.models import UploadedFile, UploadedFileEmbedding
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
    help = "Process uploaded file"

    def add_arguments(self, parser):
        parser.add_argument(
            "file_id", type=int, help="ID of the uploaded-file to process"
        )

        parser.add_argument(
            "--force",
            action="store_true",
            help="Force processing the file even if it is in COMPLETED or FAILED status.",
        )

    def handle(self, *args, **kwargs):
        file_id = kwargs["file_id"]
        force_retry = kwargs.get("force", False)

        try:
            uploaded_file = UploadedFile.objects.get(id=file_id)

            self._validate_file_size(uploaded_file)

            if not self._validate_status(uploaded_file, force=force_retry):
                self._force_cleanup(uploaded_file)

            file_name_parts = uploaded_file.file.name.split(".")
            file_extension = file_name_parts[-1] if file_name_parts else None

            if file_extension == "xlsx":
                self._handle_xlsx_attachment(uploaded_file)
            elif file_extension == "pdf":
                self._chunk_and_embed_with_rolling_buffer(
                    uploaded_file, extract_function=extract_text_from_pdf
                )
            elif file_extension == "docx":
                self._chunk_and_embed_with_rolling_buffer(
                    uploaded_file, extract_function=extract_text_from_docx
                )
            elif file_extension == "pptx":
                self._chunk_and_embed_with_rolling_buffer(
                    uploaded_file, extract_function=extract_text_from_pptx
                )
            elif file_extension == "txt":
                self._chunk_and_embed_with_rolling_buffer(
                    uploaded_file, extract_function=extract_text_from_txt
                )
            elif file_extension == "csv":
                self._chunk_and_embed_with_rolling_buffer(
                    uploaded_file, extract_function=extract_text_from_csv
                )
            else:
                self.stderr.write(
                    self.style.WARNING(f"Unsupported file type: {file_extension}")
                )
                uploaded_file.mark_as_failed("Unsupported file type.")
        except UploadedFile.DoesNotExist:
            self.stderr.write(
                self.style.ERROR(f"Uploaded file with ID {file_id} does not exist.")
            )
        except (ValueError, RuntimeError) as err:
            uploaded_file.mark_as_failed(str(err))
            self.stderr.write(self.style.ERROR(str(err)))
        except Exception as err:
            uploaded_file.mark_as_failed(str(err))
            self.stderr.write(
                self.style.ERROR(f"Error processing file with ID {file_id}: {err}")
            )

    def _validate_status(
        self, uploaded_file: UploadedFile, force: bool = False
    ) -> bool:
        """validates the status of uploaded file

        Args:
            uploaded_file (UploadedFile): the instance of UploadedFile to be validated
            force (bool, optional): flag to force process the uploaded file. Defaults to False.

        Raises:
            RuntimeError: if the status is set to PROCESSING
            RuntimeError: if the status is set to COMPLETED or FAILED, and force is set to False.

        Returns:
            bool: True if PENDING, False otherwise.
        """
        if uploaded_file.status == UploadedFile.Status.PROCESSING:
            raise RuntimeError(
                f"File with ID {uploaded_file.id} is already being processed."
            )

        if uploaded_file.status in [
            UploadedFile.Status.COMPLETED,
            UploadedFile.Status.FAILED,
        ]:
            if not force:
                raise RuntimeError(
                    f"File with ID {uploaded_file.id} has already been processed. Use --force to retry."
                )

            return False

        return True

    def _force_cleanup(self, uploaded_file: UploadedFile):
        """deletes the stored embeddings for the given file from the database

        Args:
            uploaded_file (UploadedFile): the instance of UploadedFile for which the embeddings are to be deleted
        """
        UploadedFileEmbedding.objects.filter(uploaded_file=uploaded_file).delete()
        self.stdout.write(
            self.style.WARNING(
                f"Deleted stored embeddings for file with ID {uploaded_file.id}"
            )
        )

    def _validate_file_size(self, uploaded_file: UploadedFile):
        """Validates the file size of the uploaded file.

        Args:
            uploaded_file (UploadedFile): The uploaded file to validate.

        Raises:
            ValueError: If the file size exceeds the 25MB limit.
        """
        if uploaded_file.file.size > 25 * 1024 * 1024:
            raise ValueError(
                f"Uploaded file with ID {uploaded_file.id} exceeds the size limit of 25MB."
            )

    def _chunk_and_embed_with_rolling_buffer(
        self,
        uploaded_file: UploadedFile,
        extract_function,
        buffer_size=7900,
        buffer_overlap=100,
    ):
        """
        Handle uploaded files by extracting text, chunking it, and creating embeddings.

        Args:
            uploaded_file (UploadedFile): the uploaded file to process.
            extract_function (callable): Function to extact text from the attachment.
            buffer_size (int, optional): Size of the buffer to accumulate text before processing. Defaults to 7900.
            buffer_overlap (int, optional): Number of characters to overlap between buffer chunks. Defaults to 100.
        """
        chunk_idx = 0
        rolling_buffer = ""

        uploaded_file.mark_as_processing()
        self.stdout.write(
            f"Processing uploaded file with ID {uploaded_file.id} for vectorization..."
        )

        for content in extract_function(uploaded_file.file.path):
            rolling_buffer += content

            # Process buffer when it exceeds the threshold
            while len(rolling_buffer) > (buffer_size + buffer_overlap):
                # Extract buffer content up to the threshold
                buffer_to_process = rolling_buffer[: buffer_size + buffer_overlap]
                rolling_buffer = rolling_buffer[buffer_size:]

                # Create chunks and embeddings for the buffer
                chunks = create_chunks_for_vector_embedding(buffer_to_process)
                embeddings = create_vector_embedding(chunks)
                for embedding in embeddings:
                    UploadedFileEmbedding.objects.create(
                        uploaded_file=uploaded_file,
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
                UploadedFileEmbedding.objects.create(
                    uploaded_file=uploaded_file,
                    chunk_index=chunk_idx,
                    chunk=embedding["text"],
                    embedding=embedding["embedding"],
                )
                chunk_idx += 1

        uploaded_file.mark_as_completed()

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully vectorized file with ID {uploaded_file.id}. Created {chunk_idx} embeddings."
            )
        )

    def _handle_xlsx_attachment(self, uploaded_file: UploadedFile):
        """
        Handle XLSX attachments by extracting text and creating embeddings.

        Args:
            uploaded_file (UploadedFile): The uploaded file to process.
        """
        chunk_idx = 0
        rolling_buffer = ""
        BUFFER_SIZE = 8000  # Accumulate 8000 characters before processing

        uploaded_file.mark_as_processing()

        self.stdout.write(
            f"Processing XLSX file with ID {uploaded_file.id} for vectorization..."
        )

        for sheet_content in extract_text_from_xlsx(uploaded_file.file.path):
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
                    UploadedFileEmbedding.objects.create(
                        uploaded_file=uploaded_file,
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
                UploadedFileEmbedding.objects.create(
                    uploaded_file=uploaded_file,
                    chunk_index=chunk_idx,
                    chunk=embedding["text"],
                    embedding=embedding["embedding"],
                )
                chunk_idx += 1

        uploaded_file.mark_as_completed()

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully vectorized XLSX file with ID {uploaded_file.id}. Created {chunk_idx} embeddings."
            )
        )
