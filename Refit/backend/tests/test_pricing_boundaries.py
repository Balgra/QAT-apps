"""Business-policy examples: expected numbers are independent of pricing implementation."""
from datetime import datetime, timezone

import pytest

from app.models import Product
from app.pricing import PricingEngine


TUESDAY = datetime(2030, 1, 8, 12, tzinfo=timezone.utc)


def garment(**changes):
    return Product(**{"id": 901, "name": "Fixture Shirt", "description": "An isolated pricing fixture.",
                      "category": "tops", "size": "M", "condition": "new", "price": 30,
                      "seller": "Fixture Seller", "stock": 100, "color": "Blue", **changes})


def price(quantity=1, product=None, **changes):
    options = {"shipping_method": "pickup", "coupon_code": None, "gift_wrap": False,
               "country": "SE", "customer_name": "Fixture Customer", "current_time": TUESDAY,
               "loyalty_points": 0, "first_order": True, **changes}
    return PricingEngine().calculate([(product or garment(), quantity)], **options)


@pytest.mark.parametrize("quantity,discount", [(2, 0), (3, 2.25), (4, 3), (5, 9), (6, 10.8), (7, 12.6), (8, 21.6), (9, 24.3)])
def test_quantity_campaign_boundaries(quantity, discount):
    assert price(quantity=quantity).discount == discount


@pytest.mark.parametrize("amount,discount", [(29.99, 0), (30, 3), (30.01, 3), (299.99, 30), (300, 30), (300.01, 30)])
def test_welcome_minimum_and_cap(amount, discount):
    assert price(product=garment(price=amount), coupon_code=" welcome10 ").discount == discount


def test_welcome_requires_first_order():
    assert price(coupon_code="WELCOME10", first_order=False).discount == 0


@pytest.mark.parametrize("unit,quantity,discount", [(49.99, 2, 0), (50, 2, 15), (50.01, 2, 15), (149.99, 2, 45), (150, 2, 45), (150.01, 2, 45), (100, 1, 0)])
def test_refit_coupon_minimum_item_count_and_cap(unit, quantity, discount):
    assert price(quantity, garment(price=unit), coupon_code="REFIT15").discount == discount


@pytest.mark.parametrize("points,discount", [(0, 0), (1, 0), (499, 0), (500, 6), (501, 6), (999, 6), (1000, 10), (1001, 10)])
def test_loyalty_tier_boundaries(points, discount):
    assert price(product=garment(price=100), loyalty_points=points).discount == discount


@pytest.mark.parametrize("amount,points,discount", [(200, 500, 10), (200, 1000, 20), (200.01, 1000, 20)])
def test_loyalty_reduction_caps(amount, points, discount):
    assert price(product=garment(price=amount), loyalty_points=points).discount == discount


@pytest.mark.parametrize("amount,shipping", [(119.99, 5.9), (120, 0), (120.01, 0)])
def test_free_shipping_threshold(amount, shipping):
    assert price(product=garment(price=amount), shipping_method="standard").shipping == shipping


@pytest.mark.parametrize("country,standard,express,tax", [
    ("SE", 5.9, 12.9, 7.5), ("DK", 5.9, 17.9, 7.2), ("FI", 5.9, 17.9, 7.2),
    ("NO", 9.9, 17.9, 7.5), ("DE", 9.9, 24.9, 6), ("FR", 9.9, 24.9, 6), ("US", 9.9, 24.9, 5.4),
])
def test_country_shipping_and_tax_table(country, standard, express, tax):
    assert price(country=country, shipping_method="standard").shipping == standard
    assert price(country=country, shipping_method="express").shipping == express
    assert price(country=country).tax == tax


def test_free_shipping_coupon_does_not_discount_express():
    assert price(shipping_method="standard", coupon_code="FREESHIP").shipping == 0
    assert price(shipping_method="express", coupon_code="FREESHIP").shipping == 12.9


@pytest.mark.parametrize("quantity,wrap", [(1, 3.5), (2, 3.5), (3, 6), (4, 6), (5, 6), (6, 9.5)])
def test_wrapping_quantity_boundaries(quantity, wrap):
    assert price(quantity, gift_wrap=True, shipping_method="standard").gift_wrap == wrap
    assert price(quantity, gift_wrap=True).gift_wrap == round(wrap * .8, 2)


@pytest.mark.parametrize("category,condition,size,quantity,unit,discount", [
    ("outerwear", "fair", "M", 1, 100, 4), ("outerwear", "good", "M", 1, 100, 0),
    ("outerwear", "good", "M", 2, 100, 10), ("outerwear", "new", "M", 2, 100, 4),
    ("shoes", "new", "42", 1, 100, 0), ("shoes", "like-new", "42", 1, 100, 1),
    ("shoes", "good", "42", 1, 100, 2), ("shoes", "fair", "42", 1, 100, 5),
    ("tops", "new", "S", 1, 100, 0), ("tops", "new", "S", 2, 100, 5),
    ("tops", "new", "XS", 2, 100, 5), ("accessories", "new", "OS", 2, 20, 0),
    ("accessories", "new", "OS", 3, 20, 4.8),
    ("bottoms", "new", "30", 1, 74.99, 0), ("bottoms", "new", "30", 1, 75, 0),
    ("bottoms", "new", "30", 1, 75.01, 1.13),
])
def test_category_and_condition_policy(category, condition, size, quantity, unit, discount):
    assert price(quantity, garment(category=category, condition=condition, size=size, price=unit)).discount == discount


@pytest.mark.parametrize("month,discount", [(4, 0), (5, 3.5), (6, 3.5), (7, 3.5), (8, 0)])
def test_dress_season_month_boundaries(month, discount):
    assert price(product=garment(category="dresses", price=100), current_time=datetime(2030, month, 1, tzinfo=timezone.utc)).discount == discount


@pytest.mark.parametrize("unit,discount", [(24.99, 0), (25, 1.88), (25.01, 1.88)])
def test_trio_requires_one_piece_at_or_above_25(unit, discount):
    assert price(3, garment(price=unit)).discount == discount


@pytest.mark.parametrize("amount,discount", [(149.99, 0), (150, 0), (150.01, 3)])
def test_monday_threshold(amount, discount):
    monday = datetime(2030, 1, 7, tzinfo=timezone.utc)
    assert price(product=garment(price=amount), current_time=monday).discount == discount


def test_monday_exclusion_and_combined_discount_cap():
    monday = datetime(2030, 1, 7, tzinfo=timezone.utc)
    assert price(2, garment(price=100), current_time=monday, coupon_code="REFIT15").discount == 30
    capped = price(product=garment(price=1, featured=True), coupon_code="CIRCULAR5")
    assert capped.discount == .45
    assert capped.tax == .14


def test_featured_coupon_unknown_coupon_and_demo_name_adjustment():
    assert price(product=garment(featured=True), coupon_code="CIRCULAR5").discount == 5
    assert price(coupon_code="CIRCULAR5").discount == 0
    assert price(coupon_code="UNKNOWN").discount == 0
    assert price(customer_name="  Refit Demo").discount == .01


def test_full_receipt_matches_hand_calculated_order():
    summary = price(product=garment(price=100), coupon_code="WELCOME10", shipping_method="standard", gift_wrap=True)
    assert summary.model_dump() == {"subtotal": 100, "discount": 10, "shipping": 5.9, "tax": 22.5, "gift_wrap": 3.5, "total": 121.9}
