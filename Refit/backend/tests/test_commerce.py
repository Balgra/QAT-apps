from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def shop(tmp_path):
    source = Path(__file__).parents[1] / "data" / "products.json"
    target = tmp_path / "products.json"
    target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    now = [datetime(2026, 10, 29, 12, tzinfo=timezone.utc)]
    app = create_app(target, lambda: now[0])
    return TestClient(app), app, now, target


def payload(**changes):
    return {"items": [{"product_id": 2, "quantity": 1}], "customer_name": "Test Shopper",
            "email": "guest@example.com", "address": "Example Street 12", "city": "Gothenburg",
            "postal_code": "41257", "country": "SE", "shipping_method": "standard",
            "card_number": "4242424242424242", "expiry": "12/35", "cvv": "123", **changes}


def buy(client, **changes):
    response = client.post("/api/checkout", json=payload(**changes))
    assert response.status_code == 200, response.text
    return response.json()["order_id"]


def deliver(client, order):
    assert client.patch(f"/api/orders/{order}/status", json={"status": "dispatched"}).status_code == 200
    assert client.patch(f"/api/orders/{order}/status", json={"status": "delivered"}).status_code == 200


def return_body(**changes):
    return {"product_id": 2, "quantity": 1, "reason": "fit", "condition": "unworn", "request_id": "return-1", **changes}


def test_quote_matches_checkout_and_survives_restart(shop):
    client, app, now, path = shop
    body = payload(coupon_code="WELCOME10")
    quote = client.post("/api/quote", json=body).json()
    receipt = client.post("/api/checkout", json=body).json()
    assert quote["totals"] == receipt["totals"]
    stored = TestClient(create_app(path)).get(f"/api/orders/{receipt['order_id']}").json()
    assert stored["totals"] == receipt["totals"]
    raw = path.read_text(encoding="utf-8")
    assert "4242424242424242" not in raw and '"cvv"' not in raw


def test_cancel_restores_inventory_once(shop):
    client, _, _, _ = shop
    order = buy(client)
    assert client.get("/api/products/2").json()["stock"] == 2
    assert client.post(f"/api/orders/{order}/cancel").status_code == 200
    assert client.post(f"/api/orders/{order}/cancel").status_code == 200
    assert client.get("/api/products/2").json()["stock"] == 3


def test_cancel_rejects_dispatched_order(shop):
    client, _, _, _ = shop
    order = buy(client)
    client.patch(f"/api/orders/{order}/status", json={"status": "dispatched"})
    assert client.post(f"/api/orders/{order}/cancel").status_code == 409


@pytest.mark.parametrize("days,reason,condition,expected", [
    (14, "fit", "opened", 200), (15, "fit", "unworn", 400),
    (30, "damaged", "worn", 200), (31, "damaged", "unworn", 400),
    (1, "changed-mind", "opened", 400), (1, "wrong-item", "worn", 400),
])
def test_return_boundaries(shop, days, reason, condition, expected):
    client, _, now, _ = shop
    order = buy(client)
    deliver(client, order)
    now[0] += timedelta(days=days)
    assert client.post(f"/api/orders/{order}/returns", json=return_body(reason=reason, condition=condition)).status_code == expected


def test_partial_refunds_use_original_prices_and_deduplicate(shop):
    client, _, _, _ = shop
    order = buy(client, items=[{"product_id": 2, "quantity": 2}], coupon_code="WELCOME10")
    deliver(client, order)
    original = client.get(f"/api/orders/{order}").json()["lines"][0]["paid_cents"] / 100
    client.patch("/api/products/2", json={"price": 499})
    first = client.post(f"/api/orders/{order}/returns", json=return_body()).json()
    assert client.post(f"/api/orders/{order}/returns", json=return_body()).json() == first
    second = client.post(f"/api/orders/{order}/returns", json=return_body(request_id="return-2")).json()
    assert round(first["refund"] + second["refund"], 2) == original
    assert client.post(f"/api/orders/{order}/returns", json=return_body(request_id="return-3")).status_code == 409


def test_reservation_competition_expiry_and_consumption(shop):
    client, _, now, _ = shop
    body = {"items": [{"product_id": 1, "quantity": 1}], "email": "guest@example.com"}
    hold = client.post("/api/reservations", json=body).json()
    assert client.post("/api/checkout", json=payload(items=body["items"])).status_code == 409
    order = buy(client, items=body["items"], reservation_id=hold["reservation_id"])
    assert client.get(f"/api/orders/{order}").json()["item_count"] == 1
    assert client.post("/api/checkout", json=payload(items=body["items"], reservation_id=hold["reservation_id"])).status_code == 409
    body["items"][0]["product_id"] = 4
    client.post("/api/reservations", json=body)
    now[0] += timedelta(minutes=10)
    buy(client, items=body["items"])


def test_parallel_buyers_cannot_oversell(shop):
    client, _, _, _ = shop
    with ThreadPoolExecutor(max_workers=2) as pool:
        codes = list(pool.map(lambda _: client.post("/api/checkout", json=payload(items=[{"product_id": 1, "quantity": 1}])).status_code, range(2)))
    assert sorted(codes) == [200, 409]


def test_failed_commit_preserves_order_and_stock(shop, monkeypatch):
    client, app, _, path = shop
    original = path.read_bytes()
    def fail(_):
        raise OSError("Injected storage fault")
    monkeypatch.setattr(app.state.repository.store, "commit", fail)
    with pytest.raises(OSError):
        client.post("/api/checkout", json=payload())
    assert path.read_bytes() == original


def test_seller_summary_refunds_and_reputation(shop):
    client, _, _, _ = shop
    order = buy(client)
    deliver(client, order)
    before = client.get("/api/sellers/Linnea/summary").json()
    assert before["payout"] > 0
    client.post(f"/api/orders/{order}/returns", json=return_body())
    assert client.get("/api/sellers/Linnea/summary").json()["payout"] == 0
    for _ in range(3):
        result = client.post("/api/products/2/moderation", json={"action": "approve"}).json()
    assert result["seller"]["tier"] == "trusted"
    client.post("/api/products/2/moderation", json={"action": "reject"})
    assert client.post("/api/checkout", json=payload()).status_code == 409


@pytest.mark.parametrize("country,shipping", [("US", "express"), ("DE", "pickup"), ("ZZ", "standard")])
def test_region_rules(shop, country, shipping):
    client, _, _, _ = shop
    assert client.post("/api/quote", json=payload(country=country, shipping_method=shipping)).status_code == 400


def test_profile_comes_from_backend(shop):
    client, _, _, _ = shop
    guest = client.post("/api/quote", json=payload(loyalty_points=99999)).json()["totals"]
    member = client.post("/api/quote", json=payload(email="member@refit.example")).json()["totals"]
    assert member["discount"] > guest["discount"]


def test_welcome_coupon_is_consumed_by_first_purchase(shop):
    client, _, _, _ = shop
    before = client.post("/api/quote", json=payload(coupon_code="WELCOME10")).json()["totals"]["discount"]
    buy(client, coupon_code="WELCOME10")
    after = client.post("/api/quote", json=payload(coupon_code="WELCOME10")).json()["totals"]["discount"]
    assert before > after


def test_allocated_cents_match_receipt_and_original_listings_are_kept(shop):
    client, _, _, _ = shop
    order_id = buy(client, items=[{"product_id": 2, "quantity": 2}, {"product_id": 3, "quantity": 1}], coupon_code="WELCOME10")
    order = client.get(f"/api/orders/{order_id}").json()
    totals = order["totals"]
    assert sum(row["paid_cents"] for row in order["lines"]) == round((totals["subtotal"] - totals["discount"] + totals["tax"]) * 100)
    assert client.delete("/api/products/2").status_code == 409
