from django.urls import reverse


def _get_api_url():
    return reverse("poc:litigants")


def test_with_anonymous_user(api_client):
    response = api_client.get(_get_api_url())
    assert response.status_code == 403


def test_with_no_litigants(api_client, users):
    api_client.force_authenticate(user=users["user1"])
    response = api_client.get(_get_api_url())
    assert response.status_code == 200
    assert response.data["count"] == 0
    assert response.data["results"] == []


def test_happy_path(api_client, litigants, users):
    api_client.force_authenticate(user=users["user1"])
    response = api_client.get(_get_api_url())
    assert response.status_code == 200
    assert response.data["count"] == 2
    returned_names = {litigant["name"] for litigant in response.data["results"]}
    expected_names = {litigants["mahadevan"].name, litigants["gopalan"].name}
    assert returned_names == expected_names
