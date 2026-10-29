from datetime import timedelta

import pytest

from test_commerce import shop, payload, buy, deliver, return_body


@pytest.mark.parametrize("coupon,changes,expected_fragment", [
    ("WELCOME10", {}, "Welcome discount applied"),
    ("WELCOME10", {"items": [{"product_id": 7, "quantity": 1}]}, "requires a first order"),
    ("REFIT15", {}, "requires two items"),
    ("REFIT15", {"items": [{"product_id": 3, "quantity": 2}]}, "REFIT15 campaign applied"),
    ("CIRCULAR5", {}, "Featured-piece"),
    ("CIRCULAR5", {"items": [{"product_id": 3, "quantity": 1}]}, "requires a featured"),
    ("FREESHIP", {}, "Free standard shipping"), ("unknown", {}, "Unknown coupon"),
])
def test_quote_explains_coupon_eligibility(shop, coupon, changes, expected_fragment):
    response = shop[0].post("/api/quote", json=payload(coupon_code=coupon, **changes))
    assert response.status_code == 200
    assert any(expected_fragment in text for text in response.json()["messages"])


@pytest.mark.parametrize("shipping,product_id,fragment", [("pickup", 2, "Collect"), ("express", 2, "Express delivery"), ("express", 14, "Condition check")])
def test_quote_delivery_choices(shop, shipping, product_id, fragment):
    response = shop[0].post("/api/quote", json=payload(shipping_method=shipping, items=[{"product_id": product_id, "quantity": 1}]))
    assert response.status_code == 200
    assert any(fragment in text for text in response.json()["messages"])


@pytest.mark.parametrize("changes,expected", [
    ({"items": [{"product_id": 999, "quantity": 1}]}, 404),
    ({"items": [{"product_id": 2, "quantity": 1}, {"product_id": 2, "quantity": 1}]}, 400),
    ({"reservation_id": "missing"}, 409),
])
def test_quote_rejects_invalid_carts_without_writing(shop, changes, expected):
    client, _, _, path = shop
    before = path.read_bytes()
    assert client.post("/api/quote", json=payload(**changes)).status_code == expected
    assert path.read_bytes() == before


def test_reservation_cannot_be_used_by_another_email_or_cart(shop):
    client, _, _, _ = shop
    hold = client.post("/api/reservations", json={"items": [{"product_id": 2, "quantity": 1}], "email": "guest@example.com"}).json()
    assert client.post("/api/quote", json=payload(reservation_id=hold["reservation_id"], email="other@example.com")).status_code == 409
    assert client.post("/api/quote", json=payload(reservation_id=hold["reservation_id"], items=[{"product_id": 2, "quantity": 2}])).status_code == 409


@pytest.mark.parametrize("endpoint", ["/api/quote", "/api/reservations"])
def test_fair_condition_quantity_rule_is_shared_by_quote_and_reserve(shop, endpoint):
    client, _, _, _ = shop
    client.patch("/api/products/14", json={"stock": 2})
    assert client.post(endpoint, json=payload(items=[{"product_id": 14, "quantity": 2}])).status_code == 400


def test_missing_transitions_return_and_moderation(shop):
    client, _, _, _ = shop
    assert client.patch("/api/orders/missing/status", json={"status": "dispatched"}).status_code == 404
    assert client.post("/api/orders/missing/returns", json=return_body()).status_code == 404
    assert client.post("/api/products/999/moderation", json={"action": "review"}).status_code == 404


def test_status_ordering_and_repeat_transition(shop):
    client, _, _, _ = shop
    order = buy(client)
    url = f"/api/orders/{order}/status"
    assert client.patch(url, json={"status": "delivered"}).status_code == 409
    first = client.patch(url, json={"status": "dispatched"}).json()
    assert client.patch(url, json={"status": "dispatched"}).json() == first
    assert client.post(f"/api/orders/{order}/returns", json=return_body()).status_code == 409


@pytest.mark.parametrize("quantities", [(1, 1), (2, 1)])
def test_cancellation_rejected_after_delivery_or_returns(shop, quantities):
    client, _, _, _ = shop
    purchased, returned = quantities
    order = buy(client, items=[{"product_id": 2, "quantity": purchased}])
    deliver(client, order)
    assert client.post(f"/api/orders/{order}/cancel").status_code == 409
    client.post(f"/api/orders/{order}/returns", json=return_body(quantity=returned))
    assert client.post(f"/api/orders/{order}/cancel").status_code == 409


def test_cancel_capacity_failure_is_atomic(shop):
    client, _, _, path = shop
    order = buy(client)
    client.patch("/api/products/2", json={"stock": 100})
    before = path.read_bytes()
    assert client.post(f"/api/orders/{order}/cancel").status_code == 409
    assert path.read_bytes() == before


@pytest.mark.parametrize("reason,days", [("fit", 14), ("changed-mind", 14), ("damaged", 30), ("wrong-item", 30)])
@pytest.mark.parametrize("offset,expected", [(-1, 200), (0, 200), (1, 400)])
def test_exact_return_deadline_boundaries(shop, reason, days, offset, expected):
    client, _, now, _ = shop
    order = buy(client)
    deliver(client, order)
    now[0] += timedelta(days=days, microseconds=offset)
    assert client.post(f"/api/orders/{order}/returns", json=return_body(reason=reason)).status_code == expected


@pytest.mark.parametrize("changes,expected", [
    ({"product_id": 999}, 404), ({"quantity": 0}, 422), ({"quantity": 3}, 409),
    ({"condition": "worn"}, 400), ({"reason": "unknown"}, 422),
])
def test_invalid_returns_do_not_mutate_order(shop, changes, expected):
    client, _, _, path = shop
    order = buy(client, items=[{"product_id": 2, "quantity": 2}])
    deliver(client, order)
    before = path.read_bytes()
    assert client.post(f"/api/orders/{order}/returns", json=return_body(**changes)).status_code == expected
    assert path.read_bytes() == before


def test_return_reference_cannot_be_reused_with_changed_details(shop):
    client, _, _, _ = shop
    order = buy(client, items=[{"product_id": 2, "quantity": 2}])
    deliver(client, order)
    url = f"/api/orders/{order}/returns"
    assert client.post(url, json=return_body()).status_code == 200
    assert client.post(url, json=return_body(reason="changed-mind")).status_code == 409


def test_future_delivery_and_fair_change_of_mind_rejected(shop):
    client, _, now, _ = shop
    order = buy(client, items=[{"product_id": 14, "quantity": 1}])
    deliver(client, order)
    now[0] -= timedelta(microseconds=1)
    assert client.post(f"/api/orders/{order}/returns", json=return_body(product_id=14)).status_code == 409
    now[0] += timedelta(seconds=1)
    assert client.post(f"/api/orders/{order}/returns", json=return_body(product_id=14, reason="changed-mind")).status_code == 400


@pytest.mark.parametrize("condition,reason,expected_stock", [("opened", "fit", 2), ("unworn", "damaged", 2), ("unworn", "fit", 3)])
def test_return_restock_policy(shop, condition, reason, expected_stock):
    client, _, _, _ = shop
    order = buy(client)
    deliver(client, order)
    assert client.post(f"/api/orders/{order}/returns", json=return_body(condition=condition, reason=reason)).status_code == 200
    assert client.get("/api/products/2").json()["stock"] == expected_stock


@pytest.mark.parametrize("tier,category,commission", [("standard", "tops", 12.5), ("standard", "shoes", 15), ("trusted", "outerwear", 7.5), ("trusted", "tops", 8.75), ("restricted", "tops", 18.75)])
def test_seller_commission_policy(shop, tier, category, commission):
    client, app, _, _ = shop
    client.patch("/api/products/2", json={"price": 100, "category": category, "condition": "new"})
    with app.state.repository.store.transaction() as state:
        state["sellers"]["Linnea"] = {"tier": tier, "reviews": 0, "rejections": 0}
    assert client.get("/api/sellers/Linnea/summary").json()["payout"] == 0
    order = buy(client)
    pending = client.get("/api/sellers/Linnea/summary").json()
    assert pending["payout"] == 0
    assert pending["pending_sales"] == 125
    assert pending["pending_commission"] == commission
    assert pending["pending_payout"] == 125 - commission
    deliver(client, order)
    result = client.get("/api/sellers/Linnea/summary").json()
    assert result["gross"] == 125
    assert result["commission"] == commission
    assert result["payout"] == 125 - commission
    assert client.get("/api/sellers/other/summary").json()["gross"] == 0


@pytest.mark.parametrize("price,pending", [(499.99, False), (500, False), (500.01, True)])
def test_moderation_high_value_boundary(shop, price, pending):
    client, _, _, _ = shop
    client.patch("/api/products/2", json={"price": price, "condition": "new"})
    result = client.post("/api/products/2/moderation", json={"action": "review"}).json()
    assert (result["status"] == "pending") is pending


@pytest.mark.parametrize("length,pending", [(39, True), (40, False), (41, False)])
def test_moderation_description_boundary(shop, length, pending):
    client, _, _, _ = shop
    client.patch("/api/products/2", json={"condition": "fair", "description": "x" * length})
    assert (client.post("/api/products/2/moderation", json={"action": "review"}).json()["status"] == "pending") is pending


@pytest.mark.parametrize("stock,pending", [(19, False), (20, False), (21, True)])
def test_moderation_volume_boundary(shop, stock, pending):
    client, _, _, _ = shop
    client.patch("/api/products/2", json={"stock": stock})
    assert (client.post("/api/products/2/moderation", json={"action": "review"}).json()["status"] == "pending") is pending


def test_reputation_rejection_threshold_and_trusted_high_value_review(shop):
    client, _, _, _ = shop
    for index in range(3):
        result = client.post("/api/products/2/moderation", json={"action": "reject"}).json()
        assert result["seller"]["tier"] == ("restricted" if index == 2 else "standard")
    assert "Seller requires manual approval" in client.post("/api/products/2/moderation", json={"action": "review"}).json()["reasons"]
    for _ in range(3):
        client.post("/api/products/3/moderation", json={"action": "approve"})
    client.patch("/api/products/3", json={"price": 500.01})
    assert client.post("/api/products/3/moderation", json={"action": "review"}).json()["status"] == "approved"


def test_approved_return_does_not_exceed_listing_stock_capacity(shop):
    client, _, _, _ = shop
    order = buy(client)
    deliver(client, order)
    client.patch("/api/products/2", json={"stock": 100})
    result = client.post(f"/api/orders/{order}/returns", json=return_body())
    assert result.status_code == 200 and result.json()["refund"] > 0
    assert client.get("/api/products/2").json()["stock"] == 100
