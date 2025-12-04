from django.urls import reverse


def _get_api_url():
    return reverse("poc:cases")


def test_with_anonymous_user(api_client):
    url = _get_api_url()
    response = api_client.get(url)
    assert response.status_code == 403


def test_with_no_cases(api_client, users):
    url = _get_api_url()
    api_client.force_authenticate(users["user1"])
    response = api_client.get(url)
    assert response.status_code == 200
    assert response.json()["count"] == 0


def test_happy_path(api_client, users, cases):
    url = _get_api_url()
    api_client.force_authenticate(users["user1"])
    response = api_client.get(url)
    assert response.status_code == 200
    assert response.json()["count"] == len(cases)


def test_search_by_title(api_client, users, case_factory):
    case_factory.create(title="Unique Case Title 12345")
    case_factory.create(title="Another Case Title")
    url = f"{_get_api_url()}?search=12345"
    api_client.force_authenticate(users["user1"])
    response = api_client.get(url)
    assert response.status_code == 200
    assert response.json()["count"] == 1
    assert response.json()["results"][0]["title"] == "Unique Case Title 12345"


def test_search_by_case_number(api_client, users, case_factory):
    case_factory.create(case_number="TC-2023-0001")
    case_factory.create(case_number="TC-2024-0002")
    case_factory.create(case_number="TC-2025-0003")

    url = f"{_get_api_url()}?search=TC-202"
    api_client.force_authenticate(users["user1"])
    response = api_client.get(url)
    assert response.status_code == 200
    assert response.json()["count"] == 3

    url = f"{_get_api_url()}?search=TC-2024"
    response = api_client.get(url)
    assert response.status_code == 200
    assert response.json()["count"] == 1
