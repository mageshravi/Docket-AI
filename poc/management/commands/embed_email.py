from django.core.management.base import BaseCommand
from openai import OpenAIError

from poc.models import ParsedEmail, ParsedEmailEmbedding
from poc.utils import create_chunks_for_vector_embedding, create_vector_embedding


class Command(BaseCommand):
    help = "Create vector embeddings for parsed emails in the database."

    def add_arguments(self, parser):
        parser.add_argument(
            "email_id",
            type=int,
            help="ID of the email to embed.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force vectorization even if the email is already processed.",
        )

    def handle(self, *args, **options):
        email_id = options["email_id"]
        force = options.get("force")

        self.stdout.write(f"Creating embedding for email ID {email_id}.")
        self._process_email(email_id, force=force)

    def _process_email(self, email_id: int, force: bool = False):
        try:
            email = ParsedEmail.objects.get(id=email_id)

            if email.embedding_status == ParsedEmail.EmbeddingStatus.PROCESSING:
                self.stdout.write(
                    self.style.WARNING(
                        f"Email ID {email_id} is already being processed. Skipping."
                    )
                )
                return

            if email.embedding_status in [
                ParsedEmail.EmbeddingStatus.COMPLETED,
                ParsedEmail.EmbeddingStatus.FAILED,
            ]:
                if not force:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Email ID {email_id} has already been processed. Use --force to attempt embedding again."
                        )
                    )
                    return

                # delete existing embeddings if force is used
                ParsedEmailEmbedding.objects.filter(parsed_email=email).delete()
                self.stdout.write(
                    f"Force processing of email ID {email_id}. Deleted existing embeddings."
                )

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
