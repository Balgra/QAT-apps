import pytest

from test_commerce import shop, payload


@pytest.mark.parametrize("field,value", [
    ("customer_name", "a"), ("customer_name", "    "), ("customer_name", "12345"), ("customer_name", None),
    ("email", "aaaa"), ("email", "a@b"), ("email", "a b@example.com"),
    ("address", "aaaaa"), ("address", "12345"), ("address", "   "),
    ("city", "a"), ("city", "12345"), ("postal_code", "aaaaa"),
    ("postal_code", "4125"), ("postal_code", "412577"), ("country", "AA"),
])
def test_invalid_delivery_is_field_specific_and_does_not_purchase(shop, field, value):
    client, _, _, path = shop
    original = path.read_bytes()
    response = client.post("/api/checkout", json=payload(**{field: value}))
    assert response.status_code == 422
    assert field in {error["loc"][1] for error in response.json()["detail"]}
    assert path.read_bytes() == original


def test_all_a_delivery_collects_errors_and_preserves_inventory(shop):
    client, _, _, path = shop
    original = path.read_bytes()
    body = payload(customer_name="a", email="a", address="aaaaa", city="a", postal_code="aaaaa", country="aa")
    response = client.post("/api/checkout", json=body)
    assert response.status_code == 422
    assert {"customer_name", "email", "address", "city", "postal_code", "country"} <= {error["loc"][1] for error in response.json()["detail"]}
    assert path.read_bytes() == original


@pytest.mark.parametrize("country,postal", [("SE", "41257"), ("SE", "412 57"), ("DK", "1234"), ("NO", "0123"),
                                          ("FI", "00100"), ("DE", "10115"), ("FR", "75001"), ("US", "10001"), ("US", "10001-1234")])
def test_supported_country_postal_formats_can_checkout(shop, country, postal):
    assert shop[0].post("/api/checkout", json=payload(country=country, postal_code=postal)).status_code == 200


@pytest.mark.parametrize("country,postal", [("DK", "12345"), ("NO", "123"), ("FI", "0010"), ("DE", "ABCDE"),
                                          ("FR", "7500"), ("US", "10001-123"), ("SE", "٤١٢٥٧")])
def test_wrong_country_postal_format_is_rejected(shop, country, postal):
    response = shop[0].post("/api/checkout", json=payload(country=country, postal_code=postal))
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "postal_code"]


def test_delivery_trimming_case_and_international_names(shop):
    response = shop[0].post("/api/checkout", json=payload(customer_name="  Åsa O’Neill  ", email=" guest@example.com ",
                           address=" PO Box 12 ", city=" Göteborg ", postal_code=" 412 57 ", country=" se "))
    assert response.status_code == 200
