from django.urls import reverse


def _get_api_url():
    return reverse("poc:litigants")


def test_with_anonymous_user(api_client):
    response = api_client.get(_get_api_url())
    assert response.status_code == 403


def test_with_empty_fields(api_client, users):
    api_client.force_authenticate(user=users["user1"])
    response = api_client.post(_get_api_url(), data={})
    assert response.status_code == 400
    assert "name" in response.data
    assert "bio" in response.data


def test_with_required_fields_only(api_client, users):
    api_client.force_authenticate(user=users["user1"])
    payload = {"name": "John Doe", "bio": "Dummy user for life"}
    response = api_client.post(_get_api_url(), data=payload)
    assert response.status_code == 201
    assert response.data["name"] == payload["name"]
    assert response.data["bio"] == payload["bio"]
    assert response.data["email"] == ""
    assert response.data["phone"] == ""
    assert response.data["address"] == ""
    assert response.data["notes"] == ""


def test_with_all_fields(api_client, users):
    api_client.force_authenticate(user=users["user1"])
    payload = {
        "name": "Jane Doe",
        "bio": "Another dummy user for life",
        "email": "jane.doe@example.com",
        "phone": "+1234567890",
        "address": "123 Main St, Anytown, USA",
        "notes": "This is a test note.",
    }
    response = api_client.post(_get_api_url(), data=payload)
    assert response.status_code == 201
    assert response.data["name"] == payload["name"]
    assert response.data["bio"] == payload["bio"]
    assert response.data["email"] == payload["email"]
    assert response.data["phone"] == payload["phone"]
    assert response.data["address"] == payload["address"]
    assert response.data["notes"] == payload["notes"]
