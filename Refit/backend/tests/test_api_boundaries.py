from datetime import timedelta

import pytest

from test_commerce import shop, payload
from test_pricing_boundaries import garment


def product_body(**changes):
    body = garment().model_dump(exclude={"id"})
    return {**body, **changes}


@pytest.mark.parametrize("price,expected", [(0, 422), (.01, 201), (.02, 201), (4999.99, 201), (5000, 201), (5000.01, 422), (1.001, 422)])
def test_product_price_boundaries(shop, price, expected):
    client, _, _, _ = shop
    response = client.post("/api/products", json=product_body(price=price))
    assert response.status_code == expected
    if expected == 201:
        assert client.get(f"/api/products/{response.json()['id']}").json()["price"] == price


@pytest.mark.parametrize("stock,expected", [(-1, 422), (0, 201), (1, 201), (99, 201), (100, 201), (101, 422)])
def test_product_stock_boundaries(shop, stock, expected):
    assert shop[0].post("/api/products", json=product_body(stock=stock)).status_code == expected


@pytest.mark.parametrize("field,minimum,maximum", [("name", 2, 80), ("description", 5, 500), ("seller", 2, 60), ("size", 1, 10), ("color", 3, 30)])
@pytest.mark.parametrize("position", ["below", "minimum", "maximum", "above"])
def test_listing_string_boundaries(shop, field, minimum, maximum, position):
    size = {"below": minimum - 1, "minimum": minimum, "maximum": maximum, "above": maximum + 1}[position]
    expected = 422 if position in {"below", "above"} else 201
    assert shop[0].post("/api/products", json=product_body(**{field: "a" * size})).status_code == expected


@pytest.mark.parametrize("quantity,expected", [(0, 422), (1, 200), (2, 200), (9, 200), (10, 200), (11, 422)])
def test_cart_quantity_boundaries(shop, quantity, expected):
    client, _, _, path = shop
    client.patch("/api/products/2", json={"stock": 10})
    original = path.read_bytes()
    response = client.post("/api/checkout", json=payload(items=[{"product_id": 2, "quantity": quantity}]))
    assert response.status_code == expected
    if expected != 200:
        assert path.read_bytes() == original


@pytest.mark.parametrize("quantity,expected", [(2, 200), (3, 200), (4, 409)])
def test_order_quantity_relative_to_stock(shop, quantity, expected):
    assert shop[0].post("/api/checkout", json=payload(items=[{"product_id": 2, "quantity": quantity}])).status_code == expected


@pytest.mark.parametrize("expiry,expected", [("09/26", 400), ("10/26", 200), ("11/26", 200), ("12/25", 400), ("00/35", 422), ("13/35", 422)])
def test_payment_expiry_month_boundaries(shop, expiry, expected):
    assert shop[0].post("/api/checkout", json=payload(expiry=expiry)).status_code == expected


@pytest.mark.parametrize("length,expected", [(12, 422), (13, 200), (14, 200), (18, 200), (19, 200), (20, 422)])
def test_card_length_boundaries(shop, length, expected):
    assert shop[0].post("/api/checkout", json=payload(card_number="0" * length)).status_code == expected


@pytest.mark.parametrize("cvv,expected", [("12", 422), ("123", 200), ("1234", 200), ("12345", 422), ("abc", 422)])
def test_cvv_boundaries(shop, cvv, expected):
    assert shop[0].post("/api/checkout", json=payload(cvv=cvv)).status_code == expected


@pytest.mark.parametrize("details,expected", [
    ({"items": []}, 422), ({"card_number": "4242-4242 4242-4242"}, 200),
    ({"card_number": "424242424242424x"}, 422),
    ({"items": [{"product_id": 999, "quantity": 1}]}, 404),
    ({"items": [{"product_id": 2, "quantity": 1}, {"product_id": 2, "quantity": 1}]}, 400),
])
def test_rejected_requests_preserve_state_and_formatted_card_is_accepted(shop, details, expected):
    client, _, _, path = shop
    before = path.read_bytes()
    assert client.post("/api/checkout", json=payload(**details)).status_code == expected
    if expected != 200:
        assert path.read_bytes() == before


def test_sold_out_and_fair_condition_quantity_rejections(shop):
    client, _, _, _ = shop
    client.patch("/api/products/2", json={"stock": 0})
    assert client.post("/api/checkout", json=payload()).status_code == 409
    client.patch("/api/products/14", json={"stock": 2})
    assert client.post("/api/checkout", json=payload(items=[{"product_id": 14, "quantity": 2}])).status_code == 400


@pytest.mark.parametrize("path,method", [("/api/products/999", "get"), ("/api/products/999", "delete"), ("/api/reservations/missing", "delete"), ("/api/orders/missing", "get"), ("/api/orders/missing/cancel", "post")])
def test_missing_resource_responses(shop, path, method):
    assert getattr(shop[0], method)(path).status_code == 404


def test_health_filters_and_missing_product_update(shop):
    client, _, _, _ = shop
    assert client.get("/api/health").json() == {"status": "ok"}
    assert all(p["category"] == "tops" for p in client.get("/api/products?category=tops").json())
    assert [p["id"] for p in client.get("/api/products?q=LINNEA").json()] == [2, 7, 12, 17]
    assert client.get("/api/products?q=not-present").json() == []
    assert len(client.get("/api/products?category=all").json()) == 20
    assert client.patch("/api/products/999", json={"price": 42}).status_code == 404


def test_product_patch_validation_and_empty_patch_preserve_values(shop):
    client, _, _, _ = shop
    original = client.get("/api/products/2").json()
    assert client.patch("/api/products/2", json={}).json() == original
    for patch in [{"stock": -1}, {"price": 0}, {"price": 1.001}, {"category": "unknown"}]:
        assert client.patch("/api/products/2", json=patch).status_code == 422
    assert client.get("/api/products/2").json() == original


@pytest.mark.parametrize("elapsed,available", [(timedelta(minutes=10) - timedelta(microseconds=1), False), (timedelta(minutes=10), True), (timedelta(minutes=10, microseconds=1), True)])
def test_reservation_expiry_boundary(shop, elapsed, available):
    client, _, now, _ = shop
    items = [{"product_id": 1, "quantity": 1}]
    client.post("/api/reservations", json={"items": items, "email": "owner@example.com"})
    now[0] += elapsed
    assert client.post("/api/quote", json=payload(items=items)).status_code == (200 if available else 409)


def test_reservation_release_is_repeatable_and_stock_becomes_available(shop):
    client, _, _, _ = shop
    items = [{"product_id": 1, "quantity": 1}]
    hold = client.post("/api/reservations", json={"items": items, "email": "guest@example.com"}).json()
    url = f"/api/reservations/{hold['reservation_id']}"
    assert client.delete(url).json()["status"] == "released"
    assert client.delete(url).json()["status"] == "released"
    assert client.post("/api/checkout", json=payload(items=items)).status_code == 200


@pytest.mark.parametrize("card", ["5555555555554444", "4222222222222"])
def test_luhn_doubled_digit_reduction_and_odd_length_cards(shop, card):
    assert shop[0].post("/api/checkout", json=payload(card_number=card)).status_code == 200
