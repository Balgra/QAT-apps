import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app


def make_client(tmp_path: Path) -> TestClient:
    source = Path(__file__).parents[1] / "data" / "products.json"
    target = tmp_path / "products.json"
    target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    return TestClient(create_app(target))


def test_lists_twenty_seed_products(tmp_path):
    response = make_client(tmp_path).get("/api/products")
    assert response.status_code == 200
    assert len(response.json()) == 20
    assert {row["seller"] for row in response.json()} == {"Mira", "Linnea", "Noah", "Elias", "Ava"}
    assert all(sum(row["seller"] == seller for row in response.json()) == 4 for seller in {"Mira", "Linnea", "Noah", "Elias", "Ava"})
    assert {row["stock"] for row in response.json()} == {1, 2, 3, 4}


def test_product_crud(tmp_path):
    client = make_client(tmp_path)
    payload = {"name": "Test Vest", "description": "A test-only quilted vest.", "category": "outerwear", "size": "M", "condition": "good", "price": 40, "seller": "Tester", "stock": 2, "color": "Blue", "featured": False}
    created = client.post("/api/products", json=payload)
    assert created.status_code == 201
    product_id = created.json()["id"]
    assert client.patch(f"/api/products/{product_id}", json={"price": 45}).json()["price"] == 45
    assert client.delete(f"/api/products/{product_id}").status_code == 204
    assert client.get(f"/api/products/{product_id}").status_code == 404


def test_checkout_returns_receipt_and_reduces_stock(tmp_path):
    client = make_client(tmp_path)
    response = client.post("/api/checkout", json={
        "items": [{"product_id": 2, "quantity": 1}], "customer_name": "Ada Lovelace",
        "email": "ada@example.com", "address": "1 Computing Lane", "city": "Gothenburg",
        "postal_code": "41101", "country": "SE", "card_number": "4242424242424242",
        "expiry": "12/30", "cvv": "123", "shipping_method": "standard", "gift_wrap": False,
    })
    assert response.status_code == 200
    assert response.json()["message"].startswith("Thank you")
    assert client.get("/api/products/2").json()["stock"] == 2


def test_rejects_invalid_demonstration_card(tmp_path):
    client = make_client(tmp_path)
    payload = {"items": [{"product_id": 2, "quantity": 1}], "customer_name": "Ada Lovelace", "email": "ada@example.com", "address": "1 Computing Lane", "city": "Gothenburg", "postal_code": "41101", "country": "SE", "card_number": "4242424242424241", "expiry": "12/30", "cvv": "123", "shipping_method": "standard", "gift_wrap": False}
    assert client.post("/api/checkout", json=payload).status_code == 400

