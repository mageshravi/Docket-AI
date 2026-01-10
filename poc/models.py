import re
import uuid

from django.core.validators import RegexValidator
from django.db import models
from django.utils.timezone import now
from pgvector.django import HnswIndex, VectorField

from core.models import TimestampedModel

from .managers import ActiveUploadedFilesManager
from .validators import FileValidator, validate_phone_number


def get_file_upload_path(instance, filename):
    """Generate file upload path based on case ID and current date."""
    today = now().date().strftime("%Y%m%d")
    return f"poc/uploaded_files/case_{instance.case.id}/{today}_{filename}"


class UploadedFile(TimestampedModel):
    """
    Model to store uploaded files.
    This model is used to keep track of files uploaded for processing.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    allowed_file_types = [
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
        "text/csv",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-powerpoint",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "message/rfc822",  # for EML files
    ]

    objects = models.Manager()  # The default manager.
    active_objects = (
        ActiveUploadedFilesManager()
    )  # Manager to return only non-deleted files

    file_validator = FileValidator(
        max_size_mb=10,
        allowed_mime_types=allowed_file_types,
    )
    exhibit_code_validator = RegexValidator(
        regex=r"^[A-Z][A-Z0-9-/.()]*[1-9)]$",
        flags=re.IGNORECASE,
        message="Can only contain uppercase letters, numbers, and special characters - / . ( ). Must start with a letter and end with a number or ).",
    )

    filename = models.CharField(max_length=255, blank=True)
    file = models.FileField(
        upload_to=get_file_upload_path,
        validators=[file_validator],
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    error_message = models.TextField(blank=True)
    case = models.ForeignKey(
        "Case", on_delete=models.CASCADE, related_name="uploaded_files"
    )
    exhibit_code = models.CharField(
        max_length=32,
        blank=True,
        null=True,
        validators=[exhibit_code_validator],
    )
    is_deleted = models.BooleanField(default=False)

    class Meta:
        db_table = "poc_uploaded_files"
        unique_together = (("case", "exhibit_code"),)

    def __str__(self):
        return self.file.name

    def mark_as_processing(self):
        if self.status == self.Status.PROCESSING:
            return

        self.status = self.Status.PROCESSING
        self.save(update_fields=["status"])

    def mark_as_completed(self):
        if self.status == self.Status.COMPLETED:
            return

        self.status = self.Status.COMPLETED
        self.save(update_fields=["status"])

    def mark_as_failed(self, error_message=None):
        if self.status == self.Status.FAILED:
            return

        self.status = self.Status.FAILED
        if error_message:
            self.error_message = error_message

        self.save(update_fields=["status", "error_message"])

    def mark_as_deleted(self):
        if self.is_deleted:
            return

        # Delete the file from storage
        self.file.delete(save=False)
        # Update the flag
        self.is_deleted = True
        self.save(update_fields=["is_deleted", "file"])


class ParsedEmail(TimestampedModel):
    """
    Model to store parsed email data.
    This model is used to keep track of emails that have been parsed.
    """

    class EmbeddingStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    uploaded_file = models.OneToOneField(
        UploadedFile, on_delete=models.CASCADE, related_name="parsed_email"
    )
    sent_on = models.DateTimeField()
    sender = models.EmailField()
    to_recipients = models.CharField()
    cc_recipients = models.CharField(blank=True)
    subject = models.CharField(max_length=255)
    body = models.TextField()
    cleaned_body = models.TextField()
    ai_summary = models.TextField(blank=True)
    embedding_status = models.CharField(
        max_length=20, choices=EmbeddingStatus.choices, default=EmbeddingStatus.PENDING
    )
    embedding_error_message = models.TextField(blank=True)

    class Meta:
        db_table = "poc_parsed_emails"

    def __str__(self):
        return f"{self.subject} dated {self.sent_on}"

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


class ParsedEmailAttachment(TimestampedModel):
    """
    Model to store parsed email attachments.
    This model is used to keep track of attachments from parsed emails.
    """

    class EmbeddingStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    parsed_email = models.ForeignKey(
        ParsedEmail, on_delete=models.CASCADE, related_name="parsed_attachments"
    )
    file = models.FileField(upload_to="poc/uploaded_files/attachments/")
    filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=255)
    size = models.PositiveIntegerField()  # Size in bytes
    ai_summary = models.TextField(blank=True)
    embedding_status = models.CharField(
        max_length=20, choices=EmbeddingStatus.choices, default=EmbeddingStatus.PENDING
    )
    embedding_error_message = models.TextField(blank=True)

    class Meta:
        db_table = "poc_parsed_email_attachments"

    def __str__(self):
        return self.filename

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


class ParsedEmailEmbedding(TimestampedModel):
    """
    Model to store vector embeddings for parsed emails.
    This model is used to keep track of embeddings created for parsed emails.
    """

    parsed_email = models.ForeignKey(
        ParsedEmail, on_delete=models.CASCADE, related_name="parsed_email_embeddings"
    )
    chunk_index = models.PositiveSmallIntegerField()
    chunk = models.TextField()  # The text chunk that was embedded
    embedding = VectorField(dimensions=1536)

    class Meta:
        db_table = "poc_parsed_email_embeddings"
        unique_together = (("parsed_email", "chunk_index"),)
        indexes = [
            HnswIndex(
                name="parsed_email_embedding_hnsw_idx",
                fields=["embedding"],
                m=16,
                ef_construction=200,
                opclasses=["vector_cosine_ops"],
            )
        ]

    def __str__(self):
        return f"Embedding for {self.parsed_email.subject} dated {self.parsed_email.sent_on}"


class ParsedEmailAttachmentEmbedding(TimestampedModel):
    """
    Model to store vector embeddings for parsed email attachments.
    This model is used to keep track of embeddings created for parsed email attachments.
    """

    parsed_email_attachment = models.ForeignKey(
        ParsedEmailAttachment,
        on_delete=models.CASCADE,
        related_name="parsed_email_attachment_embeddings",
    )
    chunk_index = models.PositiveSmallIntegerField()
    chunk = models.TextField()  # The text chunk that was embedded
    embedding = VectorField(dimensions=1536)

    class Meta:
        db_table = "poc_parsed_email_attachment_embeddings"
        unique_together = (("parsed_email_attachment", "chunk_index"),)
        indexes = [
            HnswIndex(
                name="parsed_email_attachment_hnswidx",  # index name cannot exceed 31 characters
                fields=["embedding"],
                m=16,
                ef_construction=200,
                opclasses=["vector_cosine_ops"],
            )
        ]

    def __str__(self):
        return f"Embedding for attachment {self.parsed_email_attachment.filename} of email {self.parsed_email_attachment.parsed_email.subject}"


class UploadedFileEmbedding(TimestampedModel):
    """
    Model to store vector embeddings of uploaded files.
    """

    uploaded_file = models.ForeignKey(
        UploadedFile,
        on_delete=models.CASCADE,
        related_name="uploaded_file_embeddings",
    )
    chunk_index = models.PositiveSmallIntegerField()
    chunk = models.TextField()
    embedding = VectorField(dimensions=1536)

    class Meta:
        db_table = "poc_uploaded_file_embeddings"
        unique_together = (("uploaded_file", "chunk_index"),)
        indexes = [
            HnswIndex(
                name="uploaded_file_mbdng_hnsw_idx",
                fields=["embedding"],
                m=16,
                ef_construction=200,
                opclasses=["vector_cosine_ops"],
            )
        ]

    def __str__(self):
        return f"Embedding for {self.uploaded_file.file.name}"


class LitigantRole(TimestampedModel):
    """
    Model to store the role of a litigant in a legal case.
    """

    name = models.CharField(max_length=255)
    handle = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "poc_litigant_roles"

    def __str__(self):
        return self.name


class Litigant(TimestampedModel):
    """
    Model to store a litigant in a legal case.
    """

    name = models.CharField(max_length=255)
    bio = models.CharField(max_length=255)
    email = models.EmailField(blank=True)
    phone = models.CharField(
        max_length=20, blank=True, validators=[validate_phone_number]
    )
    address = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    # ? Why no unique constraints.
    # * Because a litigant may be involved in different cases with different bio's/notes, and also different timelines.

    class Meta:
        db_table = "poc_litigants"

    def __str__(self):
        return f"{self.name} {self.bio}"


class Case(TimestampedModel):
    """
    Model to store a legal case.
    """

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    title = models.CharField(max_length=255)
    description = models.TextField(
        blank=True,
        help_text="Include the nature of dispute and summary of the conflict.",
    )
    litigants = models.ManyToManyField(
        Litigant, related_name="cases", through="CaseLitigant"
    )
    case_number = models.CharField(max_length=64, unique=True, blank=True, null=True)

    class Meta:
        db_table = "poc_cases"

    def __str__(self):
        return self.title


class CaseLitigant(TimestampedModel):
    """
    Model to store the relationship between a case and a litigant.
    """

    case = models.ForeignKey(
        Case, on_delete=models.CASCADE, related_name="case_litigants"
    )
    litigant = models.ForeignKey(
        Litigant, on_delete=models.CASCADE, related_name="case_litigants"
    )
    role = models.ForeignKey(
        LitigantRole, on_delete=models.CASCADE, related_name="case_litigants"
    )
    is_our_client = models.BooleanField(default=False)

    class Meta:
        db_table = "poc_case_litigants"
        unique_together = (("case", "litigant"),)

    def __str__(self):
        return f"{self.litigant} in {self.case}"


class ChatThread(TimestampedModel):
    """
    Model to store a chat thread.
    This model is used to keep track of chat conversations.
    """

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    title = models.CharField(max_length=255, blank=True)
    case = models.ForeignKey(
        Case,
        on_delete=models.CASCADE,
        related_name="chat_threads",
        blank=False,
        null=True,
    )

    class Meta:
        db_table = "poc_chat_threads"

    def __str__(self):
        return self.title if self.title else "Chat Thread"


class ChatMessage(TimestampedModel):
    """
    Model to store a chat message.
    """

    class Role(models.TextChoices):
        USER = "user", "User"
        AI = "ai", "AI"

    thread = models.ForeignKey(
        ChatThread, on_delete=models.CASCADE, related_name="messages"
    )
    role = models.CharField(max_length=10, choices=Role.choices)
    content = models.TextField()
