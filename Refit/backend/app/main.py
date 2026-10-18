from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Response, status
from fastapi.middleware.cors import CORSMiddleware

from .checkout import CheckoutService
from .models import CheckoutRequest, CheckoutResponse, Product, ProductCreate, ProductUpdate
from .pricing import PricingEngine
from .repository import ProductRepository


DEFAULT_DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "products.json"


def create_app(data_file: Path | None = None) -> FastAPI:
    app = FastAPI(title="Refit API", version="1.0.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    selected_file = data_file or Path(os.getenv("REFIT_PRODUCTS_FILE", DEFAULT_DATA_FILE))
    repository = ProductRepository(selected_file)
    checkout = CheckoutService(repository, PricingEngine())

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/products", response_model=list[Product])
    def list_products(
        category: str | None = Query(default=None, max_length=30),
        q: str | None = Query(default=None, max_length=80),
    ) -> list[Product]:
        return repository.list(category=category, query=q)

    @app.get("/api/products/{product_id}", response_model=Product)
    def get_product(product_id: int) -> Product:
        product = repository.get(product_id)
        if product is None:
            raise HTTPException(status_code=404, detail="Product not found")
        return product

    @app.post("/api/products", response_model=Product, status_code=status.HTTP_201_CREATED)
    def create_product(payload: ProductCreate) -> Product:
        return repository.create(payload)

    @app.patch("/api/products/{product_id}", response_model=Product)
    def update_product(product_id: int, payload: ProductUpdate) -> Product:
        product = repository.update(product_id, payload)
        if product is None:
            raise HTTPException(status_code=404, detail="Product not found")
        return product

    @app.delete("/api/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_product(product_id: int) -> Response:
        if not repository.delete(product_id):
            raise HTTPException(status_code=404, detail="Product not found")
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @app.post("/api/checkout", response_model=CheckoutResponse)
    def place_order(payload: CheckoutRequest) -> CheckoutResponse:
        return checkout.place_order(payload)

    return app


app = create_app()

