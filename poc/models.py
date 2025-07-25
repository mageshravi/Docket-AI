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
