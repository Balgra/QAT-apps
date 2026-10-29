from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException

from .models import CheckoutRequest, CheckoutResponse, Product
from .pricing import PricingEngine
from .repository import ProductRepository
from .commerce import CommerceService


class CheckoutService:
    def __init__(self, repository: ProductRepository, pricing: PricingEngine, commerce=None):
        self.repository = repository
        self.pricing = pricing
        self.commerce = commerce or CommerceService(repository, pricing)

    def place_order(self, request: CheckoutRequest) -> CheckoutResponse:
        lines: list[tuple[Product, int]] = []
        replacements: dict[int, Product] = {}
        seen: set[int] = set()

        for item in request.items:
            if item.product_id in seen:
                raise HTTPException(status_code=400, detail="Duplicate cart line")
            seen.add(item.product_id)
            product = self.repository.get(item.product_id)
            if product is None:
                raise HTTPException(status_code=404, detail=f"Product {item.product_id} was not found")
            if product.stock == 0:
                raise HTTPException(status_code=409, detail=f"{product.name} is sold out")
            if item.quantity > product.stock:
                raise HTTPException(status_code=409, detail=f"Only {product.stock} of {product.name} remain")
            if product.condition == "fair" and item.quantity > 1:
                raise HTTPException(status_code=400, detail="Fair-condition pieces can only be bought one at a time")
            lines.append((product, item.quantity))
            replacements[product.id] = product.model_copy(update={"stock": product.stock - item.quantity})

        digits = request.card_number
        checksum = 0
        parity = len(digits) % 2
        for index, character in enumerate(digits):
            number = int(character)
            if index % 2 == parity:
                number *= 2
                if number > 9:
                    number -= 9
            checksum += number
        if checksum % 10 != 0:
            raise HTTPException(status_code=400, detail="The demonstration card number is invalid")

        year = 2000 + int(request.expiry[3:])
        month = int(request.expiry[:2])
        now = self.commerce.clock()
        if year < now.year or (year == now.year and month < now.month):
            raise HTTPException(status_code=400, detail="The demonstration card has expired")

        return CheckoutResponse(**self.commerce.purchase(request))

