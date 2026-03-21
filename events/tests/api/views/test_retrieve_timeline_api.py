from django.urls import reverse


def _get_api_url(timeline_id):
	return reverse("events_api:timeline_detail", kwargs={"timeline_id": timeline_id})


def test_with_anonymous_user(api_client, timeline_factory, db):
	timeline = timeline_factory.create()

	response = api_client.get(_get_api_url(timeline.id))

	assert response.status_code == 403


def test_returns_timeline_for_owner(api_client, users, case_factory, timeline_factory):
	api_client.force_authenticate(user=users["user1"])

	case = case_factory.create(title="Case A")
	timeline = timeline_factory.create(
		name="Owner Timeline", case=case, created_by=users["user1"]
	)

	response = api_client.get(_get_api_url(timeline.id), format="json")

	assert response.status_code == 200
	assert response.json()["id"] == timeline.id
	assert response.json()["name"] == "Owner Timeline"
	assert response.json()["created_by"] == users["user1"].id


def test_returns_404_for_timeline_of_another_user(
	api_client, users, case_factory, timeline_factory
):
	api_client.force_authenticate(user=users["user1"])

	case = case_factory.create(title="Case A")
	timeline = timeline_factory.create(
		name="Other User Timeline", case=case, created_by=users["user2"]
	)

	response = api_client.get(_get_api_url(timeline.id), format="json")

	assert response.status_code == 404


def test_with_non_existent_timeline_returns_404(api_client, users):
	api_client.force_authenticate(user=users["user1"])

	response = api_client.get(_get_api_url(999999), format="json")

	assert response.status_code == 404
