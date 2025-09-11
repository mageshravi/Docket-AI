from uuid import uuid4

from django.urls import reverse


def _get_api_url(case_uuid, thread_uuid):
    return reverse(
        "poc:chat_messages", kwargs={"case_uuid": case_uuid, "thread_uuid": thread_uuid}
    )


def test_with_anonymous_user(api_client):
    url = _get_api_url(uuid4(), uuid4())
    response = api_client.get(url)
    assert response.status_code == 403


def test_with_non_existent_case(api_client, users):
    url = _get_api_url(uuid4(), uuid4())
    api_client.force_authenticate(users["user1"])
    response = api_client.get(url)
    assert response.status_code == 200
    assert response.json()["count"] == 0


def test_with_non_existent_thread(api_client, users, cases):
    url = _get_api_url(cases["mahadevan_vs_gopalan"].uuid, uuid4())
    api_client.force_authenticate(users["user1"])
    response = api_client.get(url)
    assert response.status_code == 200
    assert response.json()["count"] == 0


def test_with_unrelated_case_and_thread(
    api_client, users, cases, case_factory, chat_thread_factory
):
    case_2 = case_factory.create(
        title="Litigation Case 2",
        description="Description for Litigation Case 2",
    )
    thread_2 = chat_thread_factory.create(title="Chat Thread 2", case=case_2)
    url = _get_api_url(cases["mahadevan_vs_gopalan"].uuid, thread_2.uuid)
    api_client.force_authenticate(users["user1"])
    response = api_client.get(url)
    assert response.status_code == 200
    assert response.json()["count"] == 0
