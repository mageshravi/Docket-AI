from django.urls import reverse

API_URL = reverse("poc:chat_threads")


def test_with_anonymous_user(api_client):
    response = api_client.get(API_URL)
    assert response.status_code == 403


def test_with_empty_results(api_client, users):
    api_client.force_authenticate(user=users["user1"])
    response = api_client.get(API_URL)
    assert response.status_code == 200
    assert response.data["count"] == 0
    assert response.data["results"] == []


def test_happy_path(api_client, chat_thread_factory, cases, users):
    chat_thread = chat_thread_factory.create(
        case=cases["mahadevan_vs_gopalan"], title="Test Thread"
    )
    api_client.force_authenticate(user=users["user1"])
    response = api_client.get(API_URL)
    assert response.status_code == 200
    assert response.data["count"] == 1
    assert response.data["results"][0]["id"] == chat_thread.id
