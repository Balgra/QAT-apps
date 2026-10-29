from __future__ import annotations

from typing import Literal
import re

from pydantic import BaseModel, Field, ValidationInfo, field_validator


POSTAL_FORMATS = {
    "SE": (r"[0-9]{3} ?[0-9]{2}", "Use five digits, for example 41257 or 412 57."),
    "DK": (r"[0-9]{4}", "Use four digits for a Danish postal code."),
    "NO": (r"[0-9]{4}", "Use four digits for a Norwegian postal code."),
    "FI": (r"[0-9]{5}", "Use five digits for a Finnish postal code."),
    "DE": (r"[0-9]{5}", "Use five digits for a German postal code."),
    "FR": (r"[0-9]{5}", "Use five digits for a French postal code."),
    "US": (r"[0-9]{5}(-[0-9]{4})?", "Use a ZIP code such as 10001 or 10001-1234."),
}


class Product(BaseModel):
    id: int
    name: str = Field(min_length=2, max_length=80)
    description: str = Field(min_length=5, max_length=500)
    category: Literal["tops", "bottoms", "outerwear", "dresses", "shoes", "accessories"]
    size: str = Field(min_length=1, max_length=10)
    condition: Literal["new", "like-new", "good", "fair"]
    price: float = Field(gt=0, le=5000, multiple_of=0.01)
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
    price: float = Field(gt=0, le=5000, multiple_of=0.01)
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
    price: float | None = Field(default=None, gt=0, le=5000, multiple_of=0.01)
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
    country: str = Field(default="SE", min_length=2, max_length=2)
    postal_code: str = Field(min_length=3, max_length=12)
    card_number: str
    expiry: str = Field(pattern=r"^(0[1-9]|1[0-2])/[0-9]{2}$")
    cvv: str = Field(pattern=r"^[0-9]{3,4}$")
    shipping_method: Literal["standard", "express", "pickup"] = "standard"
    coupon_code: str | None = Field(default=None, max_length=24)
    gift_wrap: bool = False
    reservation_id: str | None = None

    @field_validator("customer_name", "email", "address", "city", "country", "postal_code", mode="before")
    @classmethod
    def trim_delivery(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("customer_name", "city")
    @classmethod
    def require_letters(cls, value: str) -> str:
        if not any(character.isalpha() for character in value):
            raise ValueError("Enter a name containing letters")
        return value

    @field_validator("address")
    @classmethod
    def validate_address(cls, value: str) -> str:
        if not any(character.isalpha() for character in value) or not re.search(r"[0-9]", value):
            raise ValueError("Enter a street or PO box address with a number, for example Example Street 12.")
        return value

    @field_validator("country")
    @classmethod
    def validate_country(cls, value: str) -> str:
        country = value.upper()
        if country not in POSTAL_FORMATS:
            raise ValueError("Use a supported country code: SE, DK, FI, NO, DE, FR or US.")
        return country

    @field_validator("postal_code")
    @classmethod
    def validate_postal_code(cls, value: str, info: ValidationInfo) -> str:
        country = info.data.get("country")
        if country in POSTAL_FORMATS:
            pattern, message = POSTAL_FORMATS[country]
            if not re.fullmatch(pattern, value):
                raise ValueError(message)
        elif not re.search(r"[0-9]", value):
            raise ValueError("Enter a postal code containing digits for the selected country.")
        return value

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


class QuoteRequest(BaseModel):
    items: list[CartItem] = Field(min_length=1)
    email: str = "guest@refit.example"
    customer_name: str = "Guest shopper"
    country: str = Field(default="SE", min_length=2, max_length=2)
    shipping_method: Literal["standard", "express", "pickup"] = "standard"
    coupon_code: str | None = None
    gift_wrap: bool = False
    reservation_id: str | None = None


class ReturnRequest(BaseModel):
    product_id: int
    quantity: int = Field(ge=1, le=10)
    reason: Literal["fit", "changed-mind", "damaged", "wrong-item"]
    condition: Literal["unworn", "opened", "worn"] = "unworn"
    request_id: str = Field(min_length=4, max_length=80)


class ReservationRequest(BaseModel):
    items: list[CartItem] = Field(min_length=1)
    email: str = Field(min_length=3, max_length=100)


class OrderTransition(BaseModel):
    status: Literal["dispatched", "delivered"]


class ModerationRequest(BaseModel):
    action: Literal["review", "approve", "reject"] = "review"
    note: str = Field(default="", max_length=300)

