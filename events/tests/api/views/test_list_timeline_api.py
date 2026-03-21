from uuid import uuid4

from django.urls import reverse


def _get_api_url():
    return reverse("events_api:timelines")


def test_with_anonymous_user(api_client):
    response = api_client.get(_get_api_url())
    assert response.status_code == 403


def test_returns_only_logged_in_user_timelines(
    api_client, users, case_factory, timeline_factory
):
    api_client.force_authenticate(user=users["user1"])

    case = case_factory.create(title="Case A")
    own_timeline = timeline_factory.create(
        name="Own Timeline", case=case, created_by=users["user1"]
    )
    timeline_factory.create(name="Other Timeline", case=case, created_by=users["user2"])

    response = api_client.get(_get_api_url(), format="json")

    assert response.status_code == 200
    assert response.json()["count"] == 1
    assert len(response.json()["results"]) == 1
    assert response.json()["results"][0]["id"] == own_timeline.id


def test_with_case_filter(api_client, users, case_factory, timeline_factory):
    api_client.force_authenticate(user=users["user1"])

    case_1 = case_factory.create(title="Case A")
    case_2 = case_factory.create(title="Case B")

    timeline_for_case_1 = timeline_factory.create(
        name="Case A Timeline", case=case_1, created_by=users["user1"]
    )
    timeline_factory.create(
        name="Case B Timeline", case=case_2, created_by=users["user1"]
    )

    response = api_client.get(
        _get_api_url(),
        data={"case": case_1.uuid},
        format="json",
    )

    assert response.status_code == 200
    assert response.json()["count"] == 1
    assert response.json()["results"][0]["id"] == timeline_for_case_1.id


def test_with_non_existent_case_returns_empty_results(api_client, users):
    api_client.force_authenticate(user=users["user1"])

    response = api_client.get(_get_api_url(), data={"case": uuid4()}, format="json")

    assert response.status_code == 200
    assert response.json()["count"] == 0
    assert response.json()["results"] == []


def test_browsable_api_get_does_not_trigger_case_lookup_error(api_client, users):
    api_client.force_authenticate(user=users["user1"])

    response = api_client.get(_get_api_url(), HTTP_ACCEPT="text/html")

    assert response.status_code == 200
