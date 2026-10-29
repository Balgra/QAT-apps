from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from shutil import copyfile
from tempfile import TemporaryDirectory

from fastapi import FastAPI, HTTPException, Query, Response, status
from fastapi.middleware.cors import CORSMiddleware

from .checkout import CheckoutService
from .models import CheckoutRequest, CheckoutResponse, Product, ProductCreate, ProductUpdate
from .pricing import PricingEngine
from .repository import ProductRepository
from .commerce import CommerceService
from .models import QuoteRequest, ReturnRequest, ReservationRequest, OrderTransition, ModerationRequest


DEFAULT_DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "products.json"


def create_app(data_file: Path | None = None, clock=None) -> FastAPI:
    session_directory = None
    if data_file is None:
        session_directory = TemporaryDirectory(prefix="refit-session-")
        data_file = Path(session_directory.name) / "products.json"
        copyfile(DEFAULT_DATA_FILE, data_file)

    @asynccontextmanager
    async def lifespan(app):
        try:
            yield
        finally:
            if session_directory is not None:
                session_directory.cleanup()

    app = FastAPI(title="Refit API", version="1.0.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    repository = ProductRepository(data_file)
    pricing = PricingEngine()
    commerce = CommerceService(repository, pricing, clock)
    checkout = CheckoutService(repository, pricing, commerce)
    app.state.repository = repository
    app.state.commerce = commerce

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
        with repository.store.lock:
            return repository.create(payload)

    @app.patch("/api/products/{product_id}", response_model=Product)
    def update_product(product_id: int, payload: ProductUpdate) -> Product:
        with repository.store.lock:
            product = repository.update(product_id, payload)
        if product is None:
            raise HTTPException(status_code=404, detail="Product not found")
        return product

    @app.delete("/api/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_product(product_id: int) -> Response:
        with repository.store.lock:
            state = repository.store.read()
            if any(line["product"]["id"] == product_id for order in state["orders"].values() for line in order["lines"]):
                raise HTTPException(409, "Purchased listings must remain available for order history")
            if not repository.delete(product_id):
                raise HTTPException(status_code=404, detail="Product not found")
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @app.post("/api/checkout", response_model=CheckoutResponse)
    def place_order(payload: CheckoutRequest) -> CheckoutResponse:
        return checkout.place_order(payload)

    @app.post("/api/quote")
    def quote(payload: QuoteRequest):
        return commerce.quote(payload)

    @app.post("/api/reservations", status_code=201)
    def reserve(payload: ReservationRequest):
        return commerce.reserve(payload)

    @app.delete("/api/reservations/{key}")
    def release(key: str):
        return commerce.release(key)

    @app.get("/api/orders")
    def list_orders():
        return commerce.list_orders()

    @app.get("/api/orders/{order_id}")
    def get_order(order_id: str):
        return commerce.get_order(order_id)

    @app.post("/api/orders/{order_id}/cancel")
    def cancel_order(order_id: str):
        return commerce.cancel_order(order_id)

    @app.patch("/api/orders/{order_id}/status")
    def transition(order_id: str, payload: OrderTransition):
        return commerce.transition(order_id, payload.status)

    @app.post("/api/orders/{order_id}/returns")
    def return_order(order_id: str, payload: ReturnRequest):
        return commerce.evaluate_return(order_id, payload)

    @app.get("/api/sellers/{seller}/summary")
    def seller_summary(seller: str):
        return commerce.seller_summary(seller)

    @app.post("/api/products/{product_id}/moderation")
    def moderate(product_id: int, payload: ModerationRequest):
        return commerce.moderate(product_id, payload)

    return app


app = create_app()

