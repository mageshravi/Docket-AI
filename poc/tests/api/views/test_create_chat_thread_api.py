from uuid import uuid4

from django.urls import reverse


def _get_api_url(case_uuid):
    return reverse("poc:chat_threads", kwargs={"case_uuid": case_uuid})


def test_with_anonymous_user(api_client):
    response = api_client.post(_get_api_url(uuid4()), {})
    assert response.status_code == 403


def test_with_non_existent_case(api_client, users):
    api_client.force_authenticate(users["user1"])
    response = api_client.post(_get_api_url(uuid4()), {"title": "Foo bar"})
    assert response.status_code == 404


def test_happy_path(api_client, users, cases):
    api_client.force_authenticate(user=users["user1"])
    response = api_client.post(
        _get_api_url(cases["mahadevan_vs_gopalan"].uuid),
        {"title": "Test Thread"},
    )
    assert response.status_code == 201
    assert response.data["case"] is not None
