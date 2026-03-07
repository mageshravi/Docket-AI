from django.urls import reverse

from events.models import Timeline, TimelineExhibit


def _get_api_url():
    return reverse("events:timeline")


def test_with_anonymous_user(api_client):
    response = api_client.post(_get_api_url(), data={}, format="json")
    assert response.status_code == 403


def test_with_invalid_case_id(api_client, users):
    api_client.force_authenticate(user=users["user1"])

    response = api_client.post(
        _get_api_url(),
        data={
            "name": "Valid Timeline Name",
            "case": 999999,
        },
        format="json",
    )

    assert response.status_code == 404


def test_with_duplicate_name_for_case(
    api_client, users, case_factory, uploaded_file_factory
):
    api_client.force_authenticate(user=users["user1"])

    case = case_factory.create(title="Case A")
    exhibit = uploaded_file_factory.create(
        filename="a.pdf",
        file="/tmp/a.pdf",
        case=case,
    )
    Timeline.objects.create(name="Timeline Alpha", case=case, created_by=users["user1"])

    response = api_client.post(
        _get_api_url(),
        data={
            "name": "Timeline Alpha",
            "case": case.id,
            "exhibits": [exhibit.id],
        },
        format="json",
    )

    assert response.status_code == 400
    assert "Name already exists." in str(response.json())


def test_without_exhibits_param_and_no_case_exhibits(api_client, users, case_factory):
    api_client.force_authenticate(user=users["user1"])

    case = case_factory.create(title="Case A")

    response = api_client.post(
        _get_api_url(),
        data={
            "name": "Timeline Alpha",
            "case": case.id,
        },
        format="json",
    )

    assert response.status_code == 400
    assert "exhibits" in response.json()
    assert "No exhibits are associated with this case to create timeline." in str(
        response.json()
    )


def test_with_empty_exhibits_list(api_client, users, case_factory):
    api_client.force_authenticate(user=users["user1"])

    case = case_factory.create(title="Case A")

    response = api_client.post(
        _get_api_url(),
        data={
            "name": "Timeline Alpha",
            "case": case.id,
            "exhibits": [],
        },
        format="json",
    )

    assert response.status_code == 400
    assert "exhibits" in response.json()
    assert "Exhibits list cannot be empty while creating timeline." in str(
        response.json()
    )


def test_happy_path_with_specific_exhibits(
    api_client,
    users,
    case_factory,
    uploaded_file_factory,
    monkeypatch,
    django_capture_on_commit_callbacks,
):
    api_client.force_authenticate(user=users["user1"])

    case = case_factory.create(title="Case A")
    exhibit_1 = uploaded_file_factory.create(
        filename="a.pdf",
        file="/tmp/a.pdf",
        case=case,
    )
    exhibit_2 = uploaded_file_factory.create(
        filename="b.pdf",
        file="/tmp/b.pdf",
        case=case,
    )

    timeline_processing_calls = []

    def _mock_delay(timeline_id):
        timeline_processing_calls.append(timeline_id)

    monkeypatch.setattr("events.api.views.start_timeline_processing.delay", _mock_delay)

    with django_capture_on_commit_callbacks(execute=True):
        response = api_client.post(
            _get_api_url(),
            data={
                "name": "Timeline Alpha",
                "case": case.id,
                "exhibits": [exhibit_1.id, exhibit_2.id],
            },
            format="json",
        )

    assert response.status_code == 201
    timeline = Timeline.objects.get(id=response.json()["id"])
    assert timeline.case_id == case.id
    assert timeline.name == "Timeline Alpha"
    assert timeline.created_by_id == users["user1"].id
    assert timeline_processing_calls == [timeline.id]

    timeline_exhibit_ids = set(
        TimelineExhibit.objects.filter(timeline=timeline).values_list(
            "exhibit_id", flat=True
        )
    )
    assert timeline_exhibit_ids == {exhibit_1.id, exhibit_2.id}


def test_happy_path_without_exhibits_uses_all_case_exhibits(
    api_client,
    users,
    case_factory,
    uploaded_file_factory,
    monkeypatch,
):
    api_client.force_authenticate(user=users["user1"])

    case = case_factory.create(title="Case A")
    exhibit_1 = uploaded_file_factory.create(
        filename="a.pdf",
        file="/tmp/a.pdf",
        case=case,
    )
    exhibit_2 = uploaded_file_factory.create(
        filename="b.pdf",
        file="/tmp/b.pdf",
        case=case,
    )

    monkeypatch.setattr(
        "events.api.views.start_timeline_processing.delay", lambda timeline_id: None
    )

    response = api_client.post(
        _get_api_url(),
        data={
            "name": "Timeline Alpha",
            "case": case.id,
        },
        format="json",
    )

    assert response.status_code == 201
    timeline = Timeline.objects.get(id=response.json()["id"])

    timeline_exhibit_ids = set(
        TimelineExhibit.objects.filter(timeline=timeline).values_list(
            "exhibit_id", flat=True
        )
    )
    assert timeline_exhibit_ids == {exhibit_1.id, exhibit_2.id}
