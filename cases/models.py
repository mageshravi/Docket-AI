import uuid

from django.db import models

from core.models import TimestampedModel


class Case(TimestampedModel):
    """
    Model to store a legal case.
    """

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    title = models.CharField(max_length=255)
    description = models.TextField(
        blank=True,
        help_text="Include the nature of dispute and summary of the conflict.",
    )
    litigants = models.ManyToManyField(
        "litigants.Litigant", related_name="cases", through="CaseLitigant"
    )
    case_number = models.CharField(max_length=64, unique=True, blank=True, null=True)

    class Meta:
        db_table = "poc_cases"

    def __str__(self):
        return self.title


class CaseLitigant(TimestampedModel):
    """
    Model to store the relationship between a case and a litigant.
    """

    case = models.ForeignKey(
        Case, on_delete=models.CASCADE, related_name="case_litigants"
    )
    litigant = models.ForeignKey(
        "litigants.Litigant", on_delete=models.CASCADE, related_name="case_litigants"
    )
    role = models.ForeignKey(
        "litigants.LitigantRole",
        on_delete=models.CASCADE,
        related_name="case_litigants",
    )
    is_our_client = models.BooleanField(default=False)

    class Meta:
        db_table = "poc_case_litigants"
        unique_together = (("case", "litigant"),)

    def __str__(self):
        return f"{self.litigant} in {self.case}"
