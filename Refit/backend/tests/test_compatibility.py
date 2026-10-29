"""Acceptance probes; --runxfail exposes the documented compatibility failures."""
import pytest

from test_commerce import shop, payload


def test_current_v2_client_contract(shop):
    client, _, _, _ = shop
    result = client.post("/api/quote", json=payload()).json()
    assert result["contract_version"] == "2"
    assert isinstance(result["totals"]["total"], (float, int))
    assert client.post("/api/checkout", json=payload()).status_code == 200


@pytest.mark.xfail(strict=True, reason="COMP-R1: previous client cart/id/qty fields are not translated")
def test_previous_v1_cart_contract(shop):
    client, _, _, _ = shop
    body = payload()
    body["cart"] = [{"id": 2, "qty": 1}]
    del body["items"]
    assert client.post("/api/checkout", json=body).status_code == 200


@pytest.mark.xfail(strict=True, reason="COMP-R2: previous client collection delivery enum is rejected")
def test_previous_v1_pickup_contract(shop):
    client, _, _, _ = shop
    assert client.post("/api/checkout", json=payload(shipping_method="collection")).status_code == 200
