from uuid import uuid4

from django.urls import reverse


def _get_api_url(case_uuid):
    return reverse("poc:case_detail", kwargs={"case_uuid": case_uuid})


def test_with_anonymous_user(api_client):
    response = api_client.get(_get_api_url(uuid4()))
    assert response.status_code == 403


def test_happy_path(api_client, cases, users):
    api_client.force_authenticate(user=users["user1"])
    response = api_client.get(_get_api_url(cases["mahadevan_vs_gopalan"].uuid))
    assert response.status_code == 200
    assert response.data["id"] == cases["mahadevan_vs_gopalan"].id
    assert response.data["title"] == cases["mahadevan_vs_gopalan"].title
    assert "litigants" not in response.data
