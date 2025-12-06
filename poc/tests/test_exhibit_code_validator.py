import pytest
from django.core.exceptions import ValidationError

from poc.models import UploadedFile


def test_exhibit_code_validator():
    uploaded_file = UploadedFile()

    # valid exhibit codes should pass without raising ValidationError
    uploaded_file.exhibit_code_validator("P-1")
    uploaded_file.exhibit_code_validator("C-1")
    uploaded_file.exhibit_code_validator("D-1")
    uploaded_file.exhibit_code_validator("P-3(a)")
    uploaded_file.exhibit_code_validator("PW-1/2")
    uploaded_file.exhibit_code_validator("Annexure-A1")
    uploaded_file.exhibit_code_validator("Ex.P1")

    # failure cases
    with pytest.raises(ValidationError):
        uploaded_file.exhibit_code_validator("Ex. 1")  # space not allowed

    with pytest.raises(ValidationError):
        uploaded_file.exhibit_code_validator("101")  # missing prefix

    with pytest.raises(ValidationError):
        uploaded_file.exhibit_code_validator("P-3(a")  # invalid last character
