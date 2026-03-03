from django.core.validators import MinValueValidator
from django.db import models

from core.models import TimestampedModel, User
from poc.models import Case, UploadedFile


class Timeline(TimestampedModel):
    """
    Represents a timeline of events for a specific case.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name="timelines")
    name = models.CharField(max_length=255, help_text="Name of the timeline")
    status = models.CharField(
        max_length=50,
        choices=Status.choices,
        default=Status.PENDING,
        help_text="The current status of the timeline",
    )
    created_by = models.ForeignKey(
        User,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )

    class Meta:
        db_table = "xbt_timelines"
        ordering = ["-id"]

    def __str__(self):
        return f"{self.name} ({self.case.title})"


class TimelineExhibit(TimestampedModel):
    """
    Represents an exhibit (uploaded file) that is part of a timeline.
    """

    timeline = models.ForeignKey(
        Timeline, on_delete=models.CASCADE, related_name="exhibits"
    )
    exhibit = models.ForeignKey(
        UploadedFile, on_delete=models.CASCADE, related_name="timeline_exhibits"
    )

    class Meta:
        db_table = "xbt_timeline_exhibits"

    def __str__(self):
        return f"Exhibit: {self.exhibit.filename} (Timeline: {self.timeline.name})"


class CandidateEvent(TimestampedModel):
    """
    Represents a candidate event that has been identified but not yet confirmed.
    """

    timeline_exhibit = models.ForeignKey(
        TimelineExhibit, on_delete=models.CASCADE, related_name="candidate_events"
    )
    action_phrase = models.CharField(
        max_length=255, help_text="The action phrase that indicates the event"
    )
    raw_description = models.TextField(
        help_text="The raw description of the candidate event as extracted from the source"
    )
    event_date = models.DateTimeField(
        help_text="The date and time of the candidate event occurrence"
    )
    date_confidence = models.CharField(
        max_length=50,
        help_text="The confidence level of the event date extraction (e.g., explicit, inferred, weak)",
    )
    actors = models.JSONField(
        help_text="A list of actors involved in the candidate event",
        default=list,
    )
    evidence_excerpt = models.TextField(
        help_text="An excerpt from the source that serves as evidence for the candidate event"
    )
    confidence = models.FloatField(
        validators=[MinValueValidator(0.0)],
        help_text="The confidence score of the candidate event extraction (0.0 to 1.0)",
    )
    source = models.JSONField(
        help_text="The source from which the candidate event was extracted (e.g., document, email or attachment and its metadata)",
        default=dict,
    )

    class Meta:
        db_table = "xbt_candidate_events"
        ordering = ["-id"]

    def __str__(self):
        return f"Candidate Event: '{self.raw_description}' (Timeline: {self.timeline.name})"


class TimelineEvent(TimestampedModel):
    """
    Represents a confirmed event that is part of a timeline.
    """

    class SourceEntity(models.TextChoices):
        UPLOADED_FILE = "UPLOADED_FILE", "Uploaded File"
        PARSED_EMAIL = "PARSED_EMAIL", "Parsed Email"
        PARSED_EMAIL_ATTACHMENT = "PARSED_EMAIL_ATTACHMENT", "Parsed Email Attachment"

    timeline = models.ForeignKey(
        Timeline, on_delete=models.CASCADE, related_name="events"
    )
    title = models.CharField(
        max_length=255, help_text="The title of the timeline event"
    )
    description = models.TextField(
        help_text="A brief description of the timeline event"
    )
    event_date = models.DateTimeField(
        help_text="The date and time of the timeline event occurrence"
    )
    place = models.CharField(
        max_length=255,
        blank=True,
        null=False,
        help_text="Physical or virtual location of the timeline event",
    )
    # metadata
    data = models.JSONField(help_text="Original JSON returned by the LLM")
    source_entity = models.CharField(
        max_length=50,
        choices=SourceEntity.choices,
        help_text="The entity from which this timeline event was extracted",
    )
    source_entity_id = models.PositiveIntegerField(
        validators=[MinValueValidator(1)], help_text="ID of the source entity"
    )

    class Meta:
        db_table = "xbt_timeline_events"
        ordering = ["-id"]

    def __str__(self):
        return f"{self.title} (Timeline: {self.timeline.name})"


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
    case = models.ForeignKey(
        Case, blank=False, null=True, on_delete=models.CASCADE, related_name="events"
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
