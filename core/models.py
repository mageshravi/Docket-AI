from django.contrib.auth.models import AbstractUser
from django.db import models


class TimestampedModel(models.Model):
    """
    Abstract base model that provides created and modified timestamps.
    This can be extended by other models to include timestamp fields.
    """

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class User(AbstractUser):
    """
    Custom user model that extends the default Django user model.
    This can be used to add additional fields or methods in the future.
    """

    # Additional fields can be added here if needed

    class Meta:
        db_table = "dkt_users"

    def __str__(self):
        return self.username


class VectorEmbeddableModel(models.Model):
    """
    Abstract model to indicate that this model has content that can be vector embedded.
    """

    class EmbeddingStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    embedding_status = models.CharField(
        max_length=20, choices=EmbeddingStatus.choices, default=EmbeddingStatus.PENDING
    )
    embedding_error_message = models.TextField(blank=True, default="")

    class Meta:
        abstract = True

    def mark_as_processing(self):
        if self.embedding_status == self.EmbeddingStatus.PROCESSING:
            return

        self.embedding_status = self.EmbeddingStatus.PROCESSING
        self.save(update_fields=["embedding_status"])

    def mark_as_completed(self):
        if self.embedding_status == self.EmbeddingStatus.COMPLETED:
            return

        self.embedding_status = self.EmbeddingStatus.COMPLETED
        self.save(update_fields=["embedding_status"])

    def mark_as_failed(self, error_message=None):
        if self.embedding_status == self.EmbeddingStatus.FAILED and not error_message:
            return

        self.embedding_status = self.EmbeddingStatus.FAILED
        if error_message:
            self.embedding_error_message = error_message

        self.save(update_fields=["embedding_status", "embedding_error_message"])


class EventExtractableModel(models.Model):
    """
    Abstract model to indicate that timeline events can be extracted from this model.
    """

    class EventExtractionStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        IN_PROGRESS = "in_progress", "In Progress"
        EXTRACTED = "extracted", "Extracted"
        FAILED = "failed", "Failed"

    event_extraction_status = models.CharField(
        max_length=20,
        choices=EventExtractionStatus.choices,
        default=EventExtractionStatus.PENDING,
    )
    event_extraction_error_message = models.TextField(blank=True, default="")

    class Meta:
        abstract = True

    def mark_event_extraction_in_progress(self):
        if self.event_extraction_status == self.EventExtractionStatus.IN_PROGRESS:
            return

        self.event_extraction_status = self.EventExtractionStatus.IN_PROGRESS
        self.save(update_fields=["event_extraction_status"])

    def mark_event_extraction_completed(self):
        if self.event_extraction_status == self.EventExtractionStatus.EXTRACTED:
            return

        self.event_extraction_status = self.EventExtractionStatus.EXTRACTED
        self.save(update_fields=["event_extraction_status"])

    def mark_event_extraction_failed(self, error_message=None):
        if (
            self.event_extraction_status == self.EventExtractionStatus.FAILED
            and not error_message
        ):
            return

        self.event_extraction_status = self.EventExtractionStatus.FAILED
        if error_message:
            self.event_extraction_error_message = error_message

        self.save(
            update_fields=["event_extraction_status", "event_extraction_error_message"]
        )
