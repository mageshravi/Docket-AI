from django.core.management.base import BaseCommand
from openai import OpenAIError

from poc.models import ParsedEmail, ParsedEmailEmbedding
from poc.utils import create_chunks_for_vector_embedding, create_vector_embedding


class Command(BaseCommand):
    help = "Create vector embeddings for parsed emails in the database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--email_id",
            type=int,
            help="ID of the email to embed. If not provided, all emails will be processed.",
        )
        parser.add_argument(
            "--batch_size",
            type=int,
            default=100,
            help="Number of emails to process in each batch.",
        )
        parser.add_argument(
            "--retry", action="store_true", help="Retry failed email embeddings."
        )

    def handle(self, *args, **options):
        email_id = options.get("email_id")
        batch_size = options.get("batch_size")
        retry = options.get("retry")

        if email_id:
            self.stdout.write(
                self.style.SUCCESS(f"Creating embedding for email ID {email_id}.")
            )
            self._process_email(email_id, retry=retry)
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Creating embeddings for first {batch_size} PENDING emails."
                )
            )
            emails = ParsedEmail.objects.filter(
                embedding_status=ParsedEmail.EmbeddingStatus.PENDING
            ).order_by("id")[:batch_size]
            for email in emails:
                self._process_email(email.id)

    def _process_email(self, email_id: int, retry: bool = False):
        try:
            email = ParsedEmail.objects.get(id=email_id)

            if email.embedding_status != ParsedEmail.EmbeddingStatus.PENDING:
                if email.embedding_status != ParsedEmail.EmbeddingStatus.FAILED:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Email ID {email_id} already has an embedding status of {email.embedding_status}. Skipping."
                        )
                    )
                    return

                if not retry:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Email ID {email_id} has failed status. Use --retry to attempt embedding again."
                        )
                    )
                    return

            email.mark_as_processing()

            chunks = create_chunks_for_vector_embedding(email.cleaned_body)

            embeddings = create_vector_embedding(chunks)

            for idx, embedding in enumerate(embeddings):
                ParsedEmailEmbedding.objects.create(
                    parsed_email=email,
                    chunk_index=idx,
                    chunk=embedding["text"],
                    embedding=embedding["embedding"],
                )

            email.mark_as_completed()

            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully created {len(embeddings)} embeddings for email ID {email_id}."
                )
            )
        except ParsedEmail.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f"Email with ID {email_id} does not exist.")
            )
        except OpenAIError as e:
            self.stdout.write(
                self.style.ERROR(
                    f"OpenAI API error while embedding contents of email ID {email_id}: {e}"
                )
            )
            email.mark_as_failed(error_message=str(e))
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    f"Error creating embedding for email ID {email_id}: {e}"
                )
            )
            email.mark_as_failed(error_message=str(e))
