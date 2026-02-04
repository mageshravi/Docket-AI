from django.core.validators import MinValueValidator
from django.db import models

from core.models import TimestampedModel


class Event(TimestampedModel):
    """
    Represents an event extracted from various sources.

    An event is a specific occurrence anchored in time, involving a Trigger
    (the action), Participants (the entities), and a Temporal Anchor (when it happened).
    """

    class SourceEntity(models.TextChoices):
        UPLOADED_FILE = "UPLOADED_FILE", "Uploaded File"
        PARSED_EMAIL = "PARSED_EMAIL", "Parsed Email"
        PARSED_EMAIL_ATTACHMENT = "PARSED_EMAIL_ATTACHMENT", "Parsed Email Attachment"

    # Core event fields
    title = models.CharField(max_length=255, help_text="Event title")
    description = models.TextField(
        help_text="A brief sentence containing details about trigger, participants, temporal & spatial anchors and attributes"
    )
    event_date = models.DateTimeField(help_text="Date and time of the event occurrence")
    place = models.CharField(
        max_length=255,
        blank=True,
        null=False,
        help_text="Physical or virtual location of the event",
    )

    # Custom fields (user-overridable)
    custom_title = models.CharField(
        max_length=255,
        blank=True,
        null=False,
        help_text="Custom title assigned by user",
    )
    custom_description = models.TextField(
        blank=True, null=False, help_text="Custom description assigned by user"
    )

    # Metadata
    data = models.JSONField(help_text="Original JSON returned by the LLM")
    source_entity = models.CharField(
        max_length=50,
        choices=SourceEntity.choices,
        help_text="The entity from which this event was extracted",
    )
    source_entity_id = models.PositiveIntegerField(
        validators=[MinValueValidator(1)], help_text="ID of the source entity"
    )

    class Meta:
        db_table = "xbt_events"
        ordering = ["-event_date", "-created_at"]
        indexes = [
            models.Index(fields=["source_entity", "source_entity_id"]),
            models.Index(fields=["event_date"]),
        ]

    def __str__(self):
        return f"{self.get_display_title()} - {self.event_date.strftime('%Y-%m-%d')}"

    def get_display_title(self):
        """Return custom title if set, otherwise return original title."""
        return self.custom_title if self.custom_title else self.title

    def get_display_description(self):
        """Return custom description if set, otherwise return original description."""
        return self.custom_description if self.custom_description else self.description
