import re

from django.core.exceptions import ValidationError


def validate_phone_number(value):
    """
    Validate that phone number starts with '+', then country code followed by hyphen and numbers.
    Example of valid format: +91-9876543210

    Raises:
        ValidationError: when the format is incorrect.
    """
    pattern = r"^\+\d{1,3}-\d{4,14}$"
    if not re.match(pattern, value):
        raise ValidationError(
            "Phone number must start with '+' followed by country code, hyphen, and number (e.g., +91-9876543210)."
        )
    return value
