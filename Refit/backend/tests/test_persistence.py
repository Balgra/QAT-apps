import json

import pytest

from app.models import ProductCreate, ProductUpdate
from app.repository import ProductRepository
from app.storage import StateStore
from test_pricing_boundaries import garment


@pytest.fixture
def repository(tmp_path):
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps([garment(id=1).model_dump(), garment(id=2, name="Second Item").model_dump()]), encoding="utf-8")
    return ProductRepository(path)


def test_repository_crud_bulk_replace_and_reload(repository):
    created = repository.create(ProductCreate(**garment(name="New Coat").model_dump(exclude={"id"})))
    assert created.id not in {1, 2}
    assert repository.update(created.id, ProductUpdate(price=42)).price == 42
    repository.replace_many({1: garment(id=1, price=99)})
    fresh = ProductRepository(repository.data_file)
    assert fresh.get(1).price == 99
    assert fresh.get(2).name == "Second Item"
    assert fresh.get(created.id).price == 42
    assert fresh.update(999, ProductUpdate(price=50)) is None
    assert not fresh.delete(999)
    assert fresh.delete(created.id)
    assert fresh.get(created.id) is None


def test_empty_repository_first_identifier_and_case_insensitive_search(tmp_path):
    path = tmp_path / "empty.json"
    path.write_text("[]", encoding="utf-8")
    repo = ProductRepository(path)
    assert repo.list() == []
    assert repo.create(ProductCreate(**garment().model_dump(exclude={"id"}))).id > 0
    assert len(repo.list(query="ISOLATED")) == 1
    assert len(repo.list(query="fixture seller")) == 1
    assert repo.list(category="shoes") == []


def test_legacy_list_migration_preserves_state_on_later_product_writes(repository):
    with repository.store.transaction() as state:
        state["orders"]["test-order"] = {"kept": True}
    repository.create(ProductCreate(**garment().model_dump(exclude={"id"})))
    assert StateStore(repository.data_file).read()["orders"]["test-order"] == {"kept": True}


def test_exception_in_transaction_rolls_back(repository):
    before = repository.data_file.read_bytes()
    with pytest.raises(ValueError):
        with repository.store.transaction() as state:
            state["products"][0]["stock"] = 0
            raise ValueError("Rejected business operation")
    assert repository.data_file.read_bytes() == before


def test_failed_atomic_replace_preserves_old_file_and_removes_temp(repository, monkeypatch):
    before = repository.data_file.read_bytes()
    def fail(source, destination):
        raise OSError("Injected replace failure")
    monkeypatch.setattr("app.storage.os.replace", fail)
    with pytest.raises(OSError):
        repository.update(1, ProductUpdate(price=77))
    assert repository.data_file.read_bytes() == before
    assert list(repository.data_file.parent.glob("refit-*.tmp")) == []
