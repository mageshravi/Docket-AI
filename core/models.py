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
