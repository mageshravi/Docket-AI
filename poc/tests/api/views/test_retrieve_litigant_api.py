from django.urls import reverse


def _get_api_url(litigant_id):
    return reverse(
        "poc:litigant_detail",
        kwargs={"id": litigant_id},
    )


def test_with_anonymous_user(api_client, litigants):
    response = api_client.get(_get_api_url(litigants["mahadevan"].id))
    assert response.status_code == 403


def test_with_non_existent_litigant(api_client, users):
    api_client.force_authenticate(user=users["user1"])
    response = api_client.get(_get_api_url(9999))  # Assuming 9999 does not exist
    assert response.status_code == 404


def test_happy_path(api_client, litigants, users):
    api_client.force_authenticate(user=users["user1"])
    response = api_client.get(_get_api_url(litigants["mahadevan"].id))
    assert response.status_code == 200
    assert response.data["id"] == litigants["mahadevan"].id
