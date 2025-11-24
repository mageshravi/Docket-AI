from django.urls import reverse

from poc.models import UploadedFile


def _get_api_url(case_uuid, file_id):
    return reverse(
        "poc:exhibit_detail",
        kwargs={"case_uuid": case_uuid, "id": file_id},
    )


def test_with_anonymous_user(api_client, cases):
    response = api_client.get(_get_api_url(cases["mahadevan_vs_gopalan"].uuid, 1))
    assert response.status_code == 403


def test_with_file_not_associated_with_case(api_client, cases, users, case_factory):
    api_client.force_authenticate(user=users["user1"])

    case_1 = cases["mahadevan_vs_gopalan"]

    case_foo = case_factory.create(
        title="Foo vs Bar", description="A case between Foo and Bar."
    )
    # Create an uploaded file not associated with the case_1
    other_uploaded_file = UploadedFile.objects.create(
        case=case_foo,
        filename="other_file.txt",
        file="path/to/other_file.txt",
        status=UploadedFile.Status.COMPLETED,
    )
    response = api_client.get(_get_api_url(case_1.uuid, other_uploaded_file.id))
    assert response.status_code == 404


def test_happy_path(api_client, cases, users):
    api_client.force_authenticate(user=users["user1"])
    # First, create an uploaded file instance
    uploaded_file = UploadedFile.objects.create(
        case=cases["mahadevan_vs_gopalan"],
        filename="test_file.txt",
        file="path/to/test_file.txt",
        status=UploadedFile.Status.COMPLETED,
    )
    file_id = uploaded_file.id

    # Now, retrieve the uploaded file
    response = api_client.get(_get_api_url(cases["mahadevan_vs_gopalan"].uuid, file_id))
    assert response.status_code == 200
    assert response.data["id"] == file_id
