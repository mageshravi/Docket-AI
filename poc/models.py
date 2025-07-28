from django.db import models

from core.models import TimestampedModel

from .validators import FileValidator


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

    file_validator = FileValidator(
        max_size_mb=10,
        allowed_mime_types=allowed_file_types,
    )

    file = models.FileField(
        upload_to="poc/uploaded_files/",
        validators=[file_validator],
    )
    processed = models.BooleanField(default=False)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    error_message = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "poc_uploaded_files"

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
    cc_recipients = models.CharField(blank=True, null=True)
    subject = models.CharField(max_length=255)
    body = models.TextField()
    cleaned_body = models.TextField()
    ai_summary = models.TextField(blank=True, null=True)
    embedding_status = models.CharField(
        max_length=20, choices=EmbeddingStatus.choices, default=EmbeddingStatus.PENDING
    )
    embedding_error_message = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "poc_parsed_emails"

    def __str__(self):
        return f"{self.subject} dated {self.sent_on}"


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
    ai_summary = models.TextField(blank=True, null=True)
    embedding_status = models.CharField(
        max_length=20, choices=EmbeddingStatus.choices, default=EmbeddingStatus.PENDING
    )
    embedding_error_message = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "poc_parsed_email_attachments"

    def __str__(self):
        return self.filename
