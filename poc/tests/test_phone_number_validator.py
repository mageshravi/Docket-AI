import pytest
from django.core.exceptions import ValidationError

from poc.validators import validate_phone_number


def test_phone_number_validator():
    # valid phone numbers should pass without raising ValidationError
    validate_phone_number("+1-1234567890")
    validate_phone_number("+91-9876543210")
    validate_phone_number("+44-2079460128")

    # failure cases
    with pytest.raises(ValidationError):
        validate_phone_number("1234567890")  # missing '+'

    with pytest.raises(ValidationError):
        validate_phone_number("+911234567890")  # missing hyphen

    with pytest.raises(ValidationError):
        validate_phone_number("+1-123")  # too short number
