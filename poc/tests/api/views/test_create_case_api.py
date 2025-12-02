from django.urls import reverse


def _get_api_url():
    return reverse("poc:cases")


def test_with_anonymous_user(api_client):
    url = _get_api_url()
    response = api_client.get(url)
    assert response.status_code == 403  # Unauthorized


def test_without_litigants(api_client, users):
    api_client.force_authenticate(user=users["user1"])

    # arrange
    url = _get_api_url()
    post_data = {"title": "Test Case without Litigants"}

    # act
    response = api_client.post(url, data=post_data, format="json")

    # assert
    assert response.status_code == 201
    response_data = response.json()
    assert response_data["title"] == "Test Case without Litigants"
    assert response_data["case_litigants"] == []


def test_with_invalid_litigants(api_client, users, litigants):
    api_client.force_authenticate(user=users["user1"])

    # arrange
    url = _get_api_url()
    post_data = {
        "title": "Test Case without Litigant Roles",
        "case_litigants_data": [
            {
                "litigant": litigants["mahadevan"].id,
                # missing 'role' field
            }
        ],
    }

    # act
    response = api_client.post(url, data=post_data, format="json")

    # assert
    assert response.status_code == 400
    assert "case_litigants_data" in response.json()


def test_happy_path(api_client, users, litigants, litigant_roles):
    api_client.force_authenticate(user=users["user1"])

    # arrange
    url = _get_api_url()
    post_data = {
        "title": "Test Case with Litigants",
        "description": "A test case with two litigants.",
        "case_number": "TC-001",
        "case_litigants_data": [
            {
                "litigant": litigants["mahadevan"].id,
                "role": litigant_roles["PLAINTIFF"].id,
                "is_our_client": True,
            },
            {
                "litigant": litigants["gopalan"].id,
                "role": litigant_roles["DEFENDANT"].id,
                "is_our_client": False,
            },
        ],
    }

    # act
    response = api_client.post(url, data=post_data, format="json")

    # assert
    assert response.status_code == 201
    response_data = response.json()
    import json

    print(json.dumps(response_data, indent=2))
    assert response_data["title"] == "Test Case with Litigants"
    assert len(response_data["case_litigants"]) == 2
