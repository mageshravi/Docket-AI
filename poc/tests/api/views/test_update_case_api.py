from django.urls import reverse


def _get_api_url(case_uuid):
    return reverse("poc:case_detail", kwargs={"case_uuid": case_uuid})


def test_with_anonymous_user(api_client, cases):
    url = _get_api_url(cases["mahadevan_vs_gopalan"].uuid)
    response = api_client.get(url)
    assert response.status_code == 403  # Unauthorized


# update title only
def test_update_title(api_client, users, cases):
    api_client.force_authenticate(user=users["user1"])

    # arrange
    url = _get_api_url(cases["mahadevan_vs_gopalan"].uuid)
    patch_data = {"title": "Updated Case Title"}

    # act
    response = api_client.patch(url, data=patch_data, format="json")

    # assert
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["title"] == "Updated Case Title"


# update case description only
def test_update_description(api_client, users, cases):
    api_client.force_authenticate(user=users["user1"])

    # arrange
    url = _get_api_url(cases["mahadevan_vs_gopalan"].uuid)
    patch_data = {"description": "Updated Case Description"}

    # act
    response = api_client.patch(url, data=patch_data, format="json")

    # assert
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["description"] == "Updated Case Description"


# update case number only
def test_update_case_number(api_client, users, cases):
    api_client.force_authenticate(user=users["user1"])

    # arrange
    url = _get_api_url(cases["mahadevan_vs_gopalan"].uuid)
    patch_data = {"case_number": "2024/9999"}

    # act
    response = api_client.patch(url, data=patch_data, format="json")

    # assert
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["case_number"] == "2024/9999"


# update title, description and case number together
def test_update_multiple_fields(api_client, users, cases):
    api_client.force_authenticate(user=users["user1"])

    # arrange
    url = _get_api_url(cases["mahadevan_vs_gopalan"].uuid)
    patch_data = {
        "title": "New Title",
        "description": "New Description",
        "case_number": "2024/8888",
    }

    # act
    response = api_client.patch(url, data=patch_data, format="json")

    # assert
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["title"] == "New Title"
    assert response_data["description"] == "New Description"
    assert response_data["case_number"] == "2024/8888"


# update litigants: remove all litigants
def test_update_remove_all_litigants(api_client, users, cases):
    api_client.force_authenticate(user=users["user1"])

    # arrange
    url = _get_api_url(cases["mahadevan_vs_gopalan"].uuid)
    patch_data = {"case_litigants_data": []}

    # act
    response = api_client.patch(url, data=patch_data, format="json")

    # assert
    assert response.status_code == 400
    response_data = response.json()
    assert "case_litigants_data" in response_data
    assert (
        response_data["case_litigants_data"][0]
        == "All existing litigants must be included in the case_litigants_data."
    )


# update litigants: add a new litigant
def test_update_add_new_litigant(
    api_client, users, cases, litigant_factory, litigants, litigant_roles
):
    api_client.force_authenticate(user=users["user1"])

    # arrange
    url = _get_api_url(cases["mahadevan_vs_gopalan"].uuid)
    new_litigant = litigant_factory.create(
        name="Kumar Swaminathan",
        bio="Witness in the case.",
        email="kumar.swaminathan@example.com",
        phone="+91-7890654321",
        address="789, Lakeview Apartments, Chennai, India",
    )
    patch_data = {
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
            {
                "litigant": new_litigant.id,
                "role": litigant_roles["WITNESS"].id,
                "is_our_client": False,
            },
        ]
    }

    # act
    response = api_client.patch(url, data=patch_data, format="json")

    # assert
    assert response.status_code == 200
    response_data = response.json()
    assert len(response_data["case_litigants"]) == 3
    assert response_data["case_litigants"][2]["litigant"]["name"] == "Kumar Swaminathan"
    assert response_data["case_litigants"][2]["role"]["handle"] == "WITNESS"
    assert response_data["case_litigants"][2]["is_our_client"] is False


# update litigants: update an existing litigant (should be ignored)
def test_update_existing_litigant_ignored(
    api_client, users, cases, litigants, litigant_roles
):
    api_client.force_authenticate(user=users["user1"])

    # arrange
    url = _get_api_url(cases["mahadevan_vs_gopalan"].uuid)
    patch_data = {
        "case_litigants_data": [
            {
                "litigant": litigants["mahadevan"].id,
                "role": litigant_roles["DEFENDANT"].id,  # changed role
                "is_our_client": False,  # changed is_our_client
            },
            {
                "litigant": litigants["gopalan"].id,
                "role": litigant_roles["PLAINTIFF"].id,  # changed role
                "is_our_client": True,  # changed is_our_client
            },
        ]
    }

    # act
    response = api_client.patch(url, data=patch_data, format="json")

    # assert
    assert response.status_code == 200
    response_data = response.json()
    assert len(response_data["case_litigants"]) == 2
    # roles and is_our_client should remain unchanged
    assert response_data["case_litigants"][0]["role"]["handle"] == "PLAINTIFF"
    assert response_data["case_litigants"][0]["is_our_client"] is True
    assert response_data["case_litigants"][1]["role"]["handle"] == "DEFENDANT"
    assert response_data["case_litigants"][1]["is_our_client"] is False
