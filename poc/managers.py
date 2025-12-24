from django.db import models


class ActiveUploadedFilesManager(models.Manager):
    """Manager to return only non-deleted uploaded files."""

    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)
