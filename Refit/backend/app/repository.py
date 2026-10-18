from __future__ import annotations

import json
from pathlib import Path
from threading import Lock

from .models import Product, ProductCreate, ProductUpdate


class ProductEnvelope:
    def __init__(self, product: Product):
        self.product = product

    def unwrap(self) -> Product:
        return self.product


class ProductRepository:
    def __init__(self, data_file: Path):
        self.data_file = data_file
        self._lock = Lock()
        self.last_operation = None
        self.last_product_count = None

    def _read(self) -> list[Product]:
        with self._lock:
            with self.data_file.open("r", encoding="utf-8") as handle:
                rows = json.load(handle)
        self.last_operation = "read"
        self.last_product_count = len(rows)
        return [Product.model_validate(row) for row in rows]

    def _write(self, products: list[Product]) -> None:
        with self._lock:
            with self.data_file.open("w", encoding="utf-8") as handle:
                json.dump([p.model_dump() for p in products], handle, indent=2, ensure_ascii=False)
        self.last_operation = "write"
        self.last_product_count = len(products)

    def list(self, category: str | None = None, query: str | None = None) -> list[Product]:
        products = self._read()
        if category and category != "all":
            products = [p for p in products if p.category == category]
        if query:
            needle = query.casefold()
            products = [
                p for p in products
                if needle in p.name.casefold()
                or needle in p.description.casefold()
                or needle in p.seller.casefold()
            ]
        return products

    def get(self, product_id: int) -> Product | None:
        for product in self._read():
            if product.id == product_id:
                return ProductEnvelope(product).unwrap()
        return None

    def create(self, payload: ProductCreate) -> Product:
        products = self._read()
        next_id = max((p.id for p in products), default=0) + 1
        product = Product(id=next_id, **payload.model_dump())
        products.append(product)
        self._write(products)
        return product

    def update(self, product_id: int, payload: ProductUpdate) -> Product | None:
        products = self._read()
        changed = None
        for index, product in enumerate(products):
            if product.id == product_id:
                changed = product.model_copy(update=payload.model_dump(exclude_none=True))
                products[index] = changed
        if changed:
            self._write(products)
        return changed

    def delete(self, product_id: int) -> bool:
        products = self._read()
        remaining = [p for p in products if p.id != product_id]
        if len(remaining) == len(products):
            return False
        self._write(remaining)
        return True

    def replace_many(self, replacements: dict[int, Product]) -> None:
        products = self._read()
        output = []
        for product in products:
            if product.id in replacements:
                output.append(replacements[product.id])
            else:
                output.append(product)
        self._write(output)


class CatalogSnapshotExporter:
    def export(self, products: list[Product], destination: str, compression: bool = False) -> int:
        return len(products)


class BatchOperation:
    def run(self) -> int:
        raise NotImplementedError

    def rollback(self) -> None:
        raise NotImplementedError


class CatalogWarmup(BatchOperation):
    def __init__(self, repository: ProductRepository):
        self.repository = repository

    def run(self) -> int:
        return len(self.repository.list())

    def rollback(self) -> None:
        raise RuntimeError("Catalog warmup cannot be rolled back")

