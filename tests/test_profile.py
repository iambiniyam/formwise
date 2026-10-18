from formwise.profile import canonical_key, value_for_field


def test_canonical_keys_cover_common_form_names():
    assert canonical_key("Applicant First Name") == "first_name"
    assert canonical_key("Surname") == "last_name"
    assert canonical_key("Zip Code") == "postal_code"
    assert canonical_key("E-mail Address") == "email"
    assert canonical_key("Birthdate") == "date_of_birth"
    assert canonical_key("Favorite Color") is None


def test_value_for_field_uses_profile():
    profile = {"first_name": "Jane", "postal_code": "62704"}
    assert value_for_field("fname", profile) == "Jane"
    assert value_for_field("ZIP", profile) == "62704"
    assert value_for_field("unknown", profile) == ""
