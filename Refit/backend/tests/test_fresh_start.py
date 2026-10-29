from pathlib import Path

from fastapi.testclient import TestClient

from app import main
from test_commerce import payload


def test_default_startup_uses_fresh_data_and_preserves_template(tmp_path, monkeypatch):
    source = Path(__file__).parents[1] / "data" / "products.json"
    template = tmp_path / "template.json"
    template.write_bytes(source.read_bytes())
    monkeypatch.setattr(main, "DEFAULT_DATA_FILE", template)
    original = template.read_bytes()

    first_app = main.create_app()
    runtime = first_app.state.repository.data_file
    with TestClient(first_app) as first:
        assert first.post("/api/checkout", json=payload()).status_code == 200
        assert len(first.get("/api/orders").json()) == 1
        assert first.get("/api/products/2").json()["stock"] == 2
        assert template.read_bytes() == original
    assert not runtime.exists()

    with TestClient(main.create_app()) as second:
        assert second.get("/api/orders").json() == []
        assert second.get("/api/products/2").json()["stock"] == 3
        assert second.app.state.repository.data_file != runtime
    assert template.read_bytes() == original
