from django.urls import reverse

API_URL = reverse("poc:chat_threads")


def test_with_anonymous_user(api_client):
    response = api_client.post(API_URL, {})
    assert response.status_code == 403


def test_with_non_existent_case(api_client, users):
    api_client.force_authenticate(users["user1"])
    response = api_client.post(API_URL, {"title": "Foo bar", "case": 101})
    assert response.status_code == 400
    assert response.data["case"][0] == 'Invalid pk "101" - object does not exist.'


def test_happy_path(api_client, users, cases):
    api_client.force_authenticate(user=users["user1"])
    response = api_client.post(
        API_URL,
        {"title": "Test Thread", "case": cases["mahadevan_vs_gopalan"].id},
    )
    assert response.status_code == 201
