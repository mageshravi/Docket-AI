from uuid import uuid4

from django.urls import reverse


def _get_api_url(case_uuid):
    return reverse("poc:exhibits", kwargs={"case_uuid": case_uuid})


def test_with_anonymous_user(api_client):
    url = _get_api_url(uuid4())
    response = api_client.get(url)
    assert response.status_code == 403


def test_with_non_existent_case(api_client, users):
    url = _get_api_url(uuid4())
    api_client.force_authenticate(users["user1"])
    response = api_client.get(url)
    assert response.status_code == 200
    assert response.json()["count"] == 0


def test_with_existing_uploaded_files(api_client, users, cases, uploaded_files):
    url = _get_api_url(cases["mahadevan_vs_gopalan"].uuid)
    api_client.force_authenticate(users["user1"])
    response = api_client.get(url)
    assert response.status_code == 200
    assert response.json()["count"] == 5


def test_with_search_query_param(api_client, users, cases, uploaded_files):
    url = _get_api_url(cases["mahadevan_vs_gopalan"].uuid)

    api_client.force_authenticate(users["user1"])

    # Test with a search term longer than 2 characters that matches some files
    response = api_client.get(url, {"search": "odd"})
    assert response.status_code == 200
    assert response.json()["count"] == 3  # There are 3 files with 'odd' in the name

    # Test with a search term longer than 2 characters that matches no files
    response = api_client.get(url, {"search": "nonexistent"})
    assert response.status_code == 200
    assert response.json()["count"] == 0

    # Test with a search term of 2 characters or fewer
    response = api_client.get(url, {"search": "ex"})
    assert response.status_code == 200
    assert response.json()["count"] == 0
