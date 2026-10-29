from datetime import timedelta, timezone

from fastapi.testclient import TestClient

from app.main import create_app
from test_commerce import buy, shop


def test_empty_order_list_is_read_only(shop):
    client, _, _, path = shop
    original = path.read_bytes()
    response = client.get("/api/orders")
    assert response.status_code == 200
    assert response.json() == []
    assert path.read_bytes() == original


def test_all_saved_orders_are_listed_newest_first_after_restart(shop):
    client, app, now, path = shop
    oldest = buy(client, email="first@example.com")
    assert client.post(f"/api/orders/{oldest}/cancel").status_code == 200
    now[0] += timedelta(hours=1)
    newest = buy(client, email="second@example.com")
    now[0] -= timedelta(minutes=30)
    middle = buy(client, email="third@example.com")
    # The same instant expressed in another timezone must sort by actual time.
    with app.state.repository.store.transaction() as state:
        state["orders"][middle]["created_at"] = now[0].astimezone(timezone(timedelta(hours=2))).isoformat()
    original = path.read_bytes()
    response = TestClient(create_app(path)).get("/api/orders")
    assert response.status_code == 200
    rows = response.json()
    assert [row["order_id"] for row in rows] == [newest, middle, oldest]
    assert [row["status"] for row in rows] == ["placed", "placed", "cancelled"]
    for row in rows:
        receipt = client.get(f"/api/orders/{row['order_id']}").json()
        assert row == {"order_id": receipt["order_id"], "created_at": receipt["created_at"],
                       "status": receipt["status"], "total": receipt["totals"]["total"], "item_count": receipt["item_count"]}
    assert path.read_bytes() == original
