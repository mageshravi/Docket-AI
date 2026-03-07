from django.core.validators import MinValueValidator, RegexValidator
from django.db import models

from core.models import TimestampedModel, User
from poc.models import Case, UploadedFile


class EventExtractable(models.Model):
    """
    An abstract model that represents an entity from which events can be extracted.
    This can be an uploaded file, a parsed email, or a parsed email attachment.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    event_extraction_status = models.CharField(
        max_length=50,
        choices=Status.choices,
        default=Status.PENDING,
    )

    class Meta:
        abstract = True

    def mark_as_processing(self):
        if self.event_extraction_status == self.Status.PROCESSING:
            return

        self.event_extraction_status = self.Status.PROCESSING
        self.save(update_fields=["event_extraction_status"])

    def mark_as_completed(self):
        if self.event_extraction_status == self.Status.COMPLETED:
            return

        self.event_extraction_status = self.Status.COMPLETED
        self.save(update_fields=["event_extraction_status"])

    def mark_as_failed(self):
        if self.event_extraction_status == self.Status.FAILED:
            return

        self.event_extraction_status = self.Status.FAILED
        self.save(update_fields=["event_extraction_status"])


class Timeline(TimestampedModel, EventExtractable):
    """
    Represents a timeline of events for a specific case.
    """

    # validators
    name_validator = RegexValidator(
        regex=r"^[a-zA-Z][\w\s-]+$",
        message="Timeline name must start with a letter and can only contain letters, numbers, spaces, underscores, or hyphens.",
    )

    # fields
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name="timelines")
    name = models.CharField(
        max_length=255,
        validators=[name_validator],
        help_text="Name of the timeline",
    )
    created_by = models.ForeignKey(
        User,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )
    is_active = models.BooleanField(
        default=True, help_text="Indicates whether this timeline is active"
    )

    class Meta:
        db_table = "xbt_timelines"
        unique_together = (("case", "name"),)
        ordering = ["-id"]

    def __str__(self):
        return f"{self.name} ({self.case.title})"


class TimelineExhibit(TimestampedModel, EventExtractable):
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
        blank=True,
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
