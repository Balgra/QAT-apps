from test_commerce import buy, deliver, return_body, shop


def summary(client, seller="Linnea"):
    response = client.get(f"/api/sellers/{seller}/summary")
    assert response.status_code == 200
    return response.json()


def test_earnings_move_from_pending_to_available_and_reduce_after_returns(shop):
    client, _, _, _ = shop
    client.patch("/api/products/2", json={"price": 100, "condition": "new", "size": "M"})
    order = buy(client, items=[{"product_id": 2, "quantity": 2}])
    placed = summary(client)
    assert placed["total_sales"] == placed["pending_sales"] == 250
    assert placed["pending_commission"] == 25
    assert placed["estimated_earnings"] == placed["pending_payout"] == 225
    assert placed["gross"] == placed["commission"] == placed["payout"] == 0
    client.patch(f"/api/orders/{order}/status", json={"status": "dispatched"})
    assert summary(client) == placed
    client.patch(f"/api/orders/{order}/status", json={"status": "delivered"})
    delivered = summary(client)
    assert delivered["gross"] == delivered["total_sales"] == 250
    assert delivered["commission"] == 25
    assert delivered["payout"] == delivered["estimated_earnings"] == 225
    assert delivered["pending_sales"] == delivered["pending_commission"] == delivered["pending_payout"] == 0
    assert client.post(f"/api/orders/{order}/returns", json=return_body()).status_code == 200
    partial = summary(client)
    assert partial["gross"] == partial["total_sales"] == 125
    assert partial["payout"] == partial["estimated_earnings"] == 112.5
    assert client.post(f"/api/orders/{order}/returns", json=return_body(request_id="second-return")).status_code == 200
    returned = summary(client)
    for field in ["gross", "commission", "payout", "pending_sales", "pending_commission", "pending_payout", "total_sales", "estimated_earnings"]:
        assert returned[field] == 0


def test_mixed_seller_order_and_cancellation_do_not_leak_earnings(shop):
    client, _, _, path = shop
    order = buy(client, items=[{"product_id": 2, "quantity": 1}, {"product_id": 3, "quantity": 1}])
    receipt = client.get(f"/api/orders/{order}").json()
    original = path.read_bytes()
    for line in receipt["lines"]:
        result = summary(client, line["product"]["seller"])
        assert result["pending_sales"] == result["total_sales"] == line["paid_cents"] / 100
        assert result["payout"] == 0
        assert result["estimated_earnings"] == result["pending_payout"]
    assert summary(client, "Mira")["total_sales"] == 0
    assert path.read_bytes() == original
    assert client.post(f"/api/orders/{order}/cancel").status_code == 200
    for seller in ["Linnea", "Noah"]:
        result = summary(client, seller)
        assert result["total_sales"] == result["pending_sales"] == result["estimated_earnings"] == result["payout"] == 0


def test_pending_and_delivered_orders_are_combined_without_double_counting(shop):
    client, _, _, _ = shop
    client.patch("/api/products/2", json={"price": 100, "condition": "new"})
    first = buy(client)
    deliver(client, first)
    second = buy(client)
    both = summary(client)
    assert both["total_sales"] == 250
    assert both["estimated_earnings"] == 225
    assert both["gross"] == both["pending_sales"] == 125
    assert both["payout"] == both["pending_payout"] == 112.5
    assert client.post(f"/api/orders/{second}/cancel").status_code == 200
    remaining = summary(client)
    assert remaining["total_sales"] == 125
    assert remaining["estimated_earnings"] == remaining["payout"] == 112.5
    assert remaining["pending_payout"] == 0
