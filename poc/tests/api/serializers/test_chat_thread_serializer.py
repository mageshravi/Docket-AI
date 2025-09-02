import pytest

from poc.api.serializers import ChatThreadSerializer


@pytest.mark.django_db
def test_with_invalid_case():
    invalid_data = {
        "title": "Hello World",
        "case": 101,  # Non-existent case
    }
    serializer = ChatThreadSerializer(data=invalid_data)
    assert not serializer.is_valid()
    assert "case" in serializer.errors


@pytest.mark.django_db
def test_with_empty_title(cases):
    data = {
        "title": "",
        "case": cases["mahadevan_vs_gopalan"].id,
    }
    serializer = ChatThreadSerializer(data=data)
    assert serializer.is_valid()


def test_with_long_title(cases):
    data = {
        "title": (
            "Lorem Ipsum is simply dummy text of the printing and typesetting industry."
            " Lorem Ipsum has been the industry's standard dummy text ever since the 1500s,"
            " when an unknown printer took a galley of type and scrambled it to make a type"
            " specimen book. It has survived not only five centuries, but also the leap into"
            " electronic typesetting, remaining essentially unchanged."
        ),
        "case": cases["mahadevan_vs_gopalan"].id,
    }
    serializer = ChatThreadSerializer(data=data)
    assert not serializer.is_valid()
    assert serializer.errors["title"] == [
        "Ensure this field has no more than 255 characters."
    ]


def test_with_valid_data(cases):
    data = {
        "title": (
            "Lorem Ipsum is simply dummy text of the printing and typesetting industry."
            " Lorem Ipsum has been the industry's standard dummy text ever since the 1500s,"
            " when an unknown printer took a galley of type and scrambled it to make a type"
            " specimen book."
        ),
        "case": cases["mahadevan_vs_gopalan"].id,
    }
    serializer = ChatThreadSerializer(data=data)
    assert serializer.is_valid()
