from django.urls import reverse

from events.models import TimelineExhibit


def _get_api_url(timeline_id):
    return reverse("events_api:timeline_exhibits", kwargs={"timeline_id": timeline_id})


def test_with_anonymous_user(api_client, timeline_factory, db):
    timeline = timeline_factory.create()

    response = api_client.get(_get_api_url(timeline.id))

    assert response.status_code == 403


def test_logged_in_user_can_view_only_active_timeline_exhibits(
    api_client,
    users,
    case_factory,
    timeline_factory,
    uploaded_file_factory,
):
    case = case_factory.create(title="Case A")
    timeline = timeline_factory.create(case=case, created_by=users["user1"])

    active_file = uploaded_file_factory.create(
        filename="active.pdf",
        file="/tmp/active.pdf",
        case=case,
        exhibit_code="P-1",
    )
    deleted_file = uploaded_file_factory.create(
        filename="deleted.pdf",
        file="/tmp/deleted.pdf",
        case=case,
        exhibit_code="P-2",
        is_deleted=True,
    )

    active_timeline_exhibit = TimelineExhibit.objects.create(
        timeline=timeline,
        exhibit=active_file,
    )
    TimelineExhibit.objects.create(
        timeline=timeline,
        exhibit=deleted_file,
    )

    api_client.force_authenticate(user=users["user2"])

    response = api_client.get(_get_api_url(timeline.id), format="json")

    assert response.status_code == 200
    assert response.json()["count"] == 1
    assert response.json()["next"] is None
    assert response.json()["previous"] is None

    result = response.json()["results"][0]
    assert result["id"] == active_timeline_exhibit.id
    assert result["filename"] == "active.pdf"
    assert result["exhibit_code"] == "P-1"


def test_with_non_existent_timeline_returns_404(api_client, users):
    api_client.force_authenticate(user=users["user1"])

    response = api_client.get(_get_api_url(999999), format="json")

    assert response.status_code == 404
