import magic
from django.core.exceptions import ValidationError
from django.db.models.fields.files import FieldFile
from django.utils.deconstruct import deconstructible


@deconstructible
class FileValidator:
    def __init__(self, max_size_mb=5, allowed_mime_types=None):
        self.max_size_mb = max_size_mb
        self.allowed_mime_types = allowed_mime_types or []

    def _get_mime_type(self, field_file: FieldFile):
        """
        Get the MIME type of the file.
        This is a placeholder for actual MIME type detection logic.
        """
        initial_position = field_file.file.tell()

        # Seek to the start of the file to read content
        field_file.file.seek(0)

        # Read a chunk (e.g., first 2048 bytes) for mime detection
        file_sample = field_file.file.read(2048)

        # Use python-magic to detect MIME type
        mime_type = magic.from_buffer(file_sample, mime=True)

        # Reset file pointer to original position (important for further reading)
        field_file.file.seek(initial_position)

        return mime_type

    def validate_file_type(self, file):
        """
        Validate the MIME type of the uploaded file.
        Raises ValidationError if the file type is not in the allowed list.
        """
        mime_type = self._get_mime_type(file)
        if mime_type not in self.allowed_mime_types:
            raise ValidationError(
                f"File type {mime_type} is not allowed. Allowed types: {', '.join(self.allowed_mime_types)}."
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
