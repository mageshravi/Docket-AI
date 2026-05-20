from django.db import models

from core.models import TimestampedModel

from .validators import validate_phone_number


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
