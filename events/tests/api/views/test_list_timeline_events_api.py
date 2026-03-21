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

	older_event = TimelineEvent.objects.create(
		timeline=timeline,
		title="Older Event",
		description="Older description",
		event_date=timezone.now(),
		place="Court Hall 1",
		data={"source": "test"},
		source_entity=TimelineEvent.SourceEntity.UPLOADED_FILE,
		source_entity_id=1,
	)
	newer_event = TimelineEvent.objects.create(
		timeline=timeline,
		title="Newer Event",
		description="Newer description",
		event_date=timezone.now(),
		place="",
		data={"source": "test"},
		source_entity=TimelineEvent.SourceEntity.UPLOADED_FILE,
		source_entity_id=2,
	)

	api_client.force_authenticate(user=users["user2"])

	response = api_client.get(_get_api_url(timeline.id), format="json")

	assert response.status_code == 200
	assert response.json()["count"] == 2
	assert response.json()["next"] is None
	assert response.json()["previous"] is None

	first_result = response.json()["results"][0]
	second_result = response.json()["results"][1]

	assert first_result["id"] == newer_event.id
	assert first_result["title"] == "Newer Event"
	assert first_result["description"] == "Newer description"
	assert first_result["event_date"] is not None
	assert first_result["place"] == ""

	assert second_result["id"] == older_event.id
	assert second_result["title"] == "Older Event"
	assert second_result["place"] == "Court Hall 1"


def test_with_non_existent_timeline_returns_404(api_client, users):
	api_client.force_authenticate(user=users["user1"])

	response = api_client.get(_get_api_url(999999), format="json")

	assert response.status_code == 404
