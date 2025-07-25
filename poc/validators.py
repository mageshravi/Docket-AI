from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible


@deconstructible
class FileValidator:
    def __init__(self, max_size_mb=5, allowed_mime_types=None):
        self.max_size_mb = max_size_mb
        self.allowed_mime_types = allowed_mime_types or []

    def validate_file_type(self, file):
        """
        Validate the MIME type of the uploaded file.
        Raises ValidationError if the file type is not in the allowed list.
        """
        if file.content_type not in self.allowed_mime_types:
            raise ValidationError(
                f"File type {file.content_type} is not allowed. Allowed types: {', '.join(self.allowed_mime_types)}."
            )

        return file

    def validate_file_size(self, file):
        """
        Validate the size of the uploaded file.
        Raises ValidationError if the file size exceeds the specified limit.
        """
        max_size_bytes = self.max_size_mb * 1024 * 1024
        if file.size > max_size_bytes:
            raise ValidationError(f"File size should not exceed {self.max_size_mb} MB.")

        return file

    def __call__(self, file):
        self.validate_file_type(file)
        self.validate_file_size(file)
