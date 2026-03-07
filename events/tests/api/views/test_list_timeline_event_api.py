from django.urls import reverse
from django.utils import timezone

from events.models import TimelineEvent


def _get_api_url(timeline_id):
    return reverse("events_api:timeline_events", kwargs={"timeline_id": timeline_id})


def test_with_anonymous_user(api_client, timeline_factory, db):
    timeline = timeline_factory.create()

    response = api_client.get(_get_api_url(timeline.id))

    assert response.status_code == 403


def test_logged_in_user_can_view_any_timeline_events(
    api_client,
    users,
    case_factory,
    timeline_factory,
):
    case = case_factory.create(title="Case A")
    timeline = timeline_factory.create(case=case, created_by=users["user1"])

    event = TimelineEvent.objects.create(
        timeline=timeline,
        title="Event title",
        description="Event description",
        event_date=timezone.now(),
        place="",
        data={"source": "test"},
        source_entity=TimelineEvent.SourceEntity.UPLOADED_FILE,
        source_entity_id=1,
    )

    api_client.force_authenticate(user=users["user2"])

    response = api_client.get(_get_api_url(timeline.id), format="json")

    assert response.status_code == 200
    assert response.json()["count"] == 1
    assert response.json()["next"] is None
    assert response.json()["previous"] is None

    result = response.json()["results"][0]
    assert result["id"] == event.id
    assert result["title"] == "Event title"
    assert result["description"] == "Event description"
    assert result["event_date"] is not None
    assert result["place"] is None
    assert result["created_at"] is not None
    assert result["updated_at"] is not None


def test_with_non_existent_timeline_returns_404(api_client, users):
    api_client.force_authenticate(user=users["user1"])

    response = api_client.get(_get_api_url(999999), format="json")

    assert response.status_code == 404
