from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class Product(BaseModel):
    id: int
    name: str = Field(min_length=2, max_length=80)
    description: str = Field(min_length=5, max_length=500)
    category: Literal["tops", "bottoms", "outerwear", "dresses", "shoes", "accessories"]
    size: str = Field(min_length=1, max_length=10)
    condition: Literal["new", "like-new", "good", "fair"]
    price: float = Field(gt=0, le=5000)
    seller: str = Field(min_length=2, max_length=60)
    stock: int = Field(ge=0, le=100)
    color: str = Field(min_length=3, max_length=30)
    featured: bool = False


class ProductCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    description: str = Field(min_length=5, max_length=500)
    category: Literal["tops", "bottoms", "outerwear", "dresses", "shoes", "accessories"]
    size: str = Field(min_length=1, max_length=10)
    condition: Literal["new", "like-new", "good", "fair"]
    price: float = Field(gt=0, le=5000)
    seller: str = Field(min_length=2, max_length=60)
    stock: int = Field(ge=0, le=100)
    color: str = Field(min_length=3, max_length=30)
    featured: bool = False


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=80)
    description: str | None = Field(default=None, min_length=5, max_length=500)
    category: Literal["tops", "bottoms", "outerwear", "dresses", "shoes", "accessories"] | None = None
    size: str | None = Field(default=None, min_length=1, max_length=10)
    condition: Literal["new", "like-new", "good", "fair"] | None = None
    price: float | None = Field(default=None, gt=0, le=5000)
    seller: str | None = Field(default=None, min_length=2, max_length=60)
    stock: int | None = Field(default=None, ge=0, le=100)
    color: str | None = Field(default=None, min_length=3, max_length=30)
    featured: bool | None = None


class CartItem(BaseModel):
    product_id: int
    quantity: int = Field(ge=1, le=10)


class CheckoutRequest(BaseModel):
    items: list[CartItem] = Field(min_length=1)
    customer_name: str = Field(min_length=2, max_length=80)
    email: str = Field(pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    address: str = Field(min_length=5, max_length=180)
    city: str = Field(min_length=2, max_length=80)
    postal_code: str = Field(min_length=3, max_length=12)
    country: str = Field(default="SE", min_length=2, max_length=2)
    card_number: str
    expiry: str = Field(pattern=r"^(0[1-9]|1[0-2])/[0-9]{2}$")
    cvv: str = Field(pattern=r"^[0-9]{3,4}$")
    shipping_method: Literal["standard", "express", "pickup"] = "standard"
    coupon_code: str | None = Field(default=None, max_length=24)
    gift_wrap: bool = False

    @field_validator("card_number")
    @classmethod
    def clean_card_number(cls, value: str) -> str:
        digits = value.replace(" ", "").replace("-", "")
        if not digits.isdigit() or not 13 <= len(digits) <= 19:
            raise ValueError("Card number must contain 13 to 19 digits")
        return digits


class PriceSummary(BaseModel):
    subtotal: float
    discount: float
    shipping: float
    tax: float
    gift_wrap: float
    total: float


class CheckoutResponse(BaseModel):
    order_id: str
    message: str
    totals: PriceSummary
    item_count: int

