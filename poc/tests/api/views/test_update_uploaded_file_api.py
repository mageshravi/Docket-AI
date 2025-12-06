from django.urls import reverse


def _get_api_url(case_uuid: str, file_id: int) -> str:
    return reverse("poc:exhibit_detail", kwargs={"case_uuid": case_uuid, "id": file_id})


def test_with_anonymous_user(api_client, uploaded_files):
    uploaded_file = uploaded_files[0]
    url = _get_api_url(uploaded_file.case.uuid, uploaded_file.id)
    response = api_client.patch(url, data={"exhibit_code": "A123"})
    assert response.status_code == 403


def test_with_field_other_than_exhibit_code(api_client, users, uploaded_files):
    uploaded_file = uploaded_files[0]
    url = _get_api_url(uploaded_file.case.uuid, uploaded_file.id)
    api_client.force_authenticate(user=users["user1"])
    response = api_client.patch(
        url, data={"exhibit_code": "A123", "file": "new_file.txt"}
    )
    assert response.status_code == 400
    assert response.data["detail"] == "Only 'exhibit_code' field can be updated."


def test_set_duplicate_exhibit_code(api_client, users, uploaded_files):
    uploaded_file1 = uploaded_files[0]
    uploaded_file2 = uploaded_files[1]
    url = _get_api_url(uploaded_file2.case.uuid, uploaded_file2.id)
    api_client.force_authenticate(user=users["user1"])
    response = api_client.patch(url, data={"exhibit_code": uploaded_file1.exhibit_code})
    assert response.status_code == 400
    assert "non_field_errors" in response.data


def test_set_invalid_exhibit_code(api_client, users, uploaded_files):
    uploaded_file = uploaded_files[0]
    url = _get_api_url(uploaded_file.case.uuid, uploaded_file.id)
    api_client.force_authenticate(user=users["user1"])
    response = api_client.patch(url, data={"exhibit_code": "invalid_code!"})
    assert response.status_code == 400
    assert "exhibit_code" in response.data


def test_set_exhibit_code(api_client, users, uploaded_files):
    uploaded_file = uploaded_files[0]
    url = _get_api_url(uploaded_file.case.uuid, uploaded_file.id)
    api_client.force_authenticate(user=users["user1"])
    response = api_client.patch(url, data={"exhibit_code": "P-1"})
    assert response.status_code == 200
    assert response.data["id"] == uploaded_file.id
    assert response.data["exhibit_code"] == "P-1"


def test_unset_exhibit_code(api_client, users, uploaded_files):
    import json

    uploaded_file = uploaded_files[0]
    url = _get_api_url(uploaded_file.case.uuid, uploaded_file.id)
    api_client.force_authenticate(user=users["user1"])
    data = {"exhibit_code": None}
    response = api_client.patch(
        url, data=json.dumps(data), content_type="application/json"
    )
    assert response.status_code == 200
