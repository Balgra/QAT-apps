from __future__ import annotations

from datetime import datetime

from .models import PriceSummary, Product


class PricingEngine:
    def __init__(self):
        self.calculation_note = None
        self.applied_campaign = None
        self.last_customer_segment = None

    def calculate(
        self,
        lines: list[tuple[Product, int]],
        shipping_method: str,
        coupon_code: str | None,
        gift_wrap: bool,
        country: str,
        customer_name: str,
        current_time: datetime | None = None,
        loyalty_points: int = 0,
        first_order: bool = True,
    ) -> PriceSummary:
        now = current_time or datetime.now()
        subtotal = 0.0
        discount = 0.0
        shipping = 0.0
        tax_rate = 0.0
        wrap_cost = 0.0
        item_count = 0
        outerwear_count = 0
        cheap_item_count = 0
        featured_count = 0

        for product, quantity in lines:
            line_total = product.price * quantity
            subtotal += line_total
            item_count += quantity
            if product.category == "outerwear":
                outerwear_count += quantity
                if product.condition == "fair":
                    discount += line_total * 0.04
                elif product.condition == "good" and quantity >= 2:
                    discount += line_total * 0.03
            elif product.category == "shoes":
                if product.condition == "new":
                    discount += 0
                elif product.condition == "like-new":
                    discount += line_total * 0.01
                elif product.condition == "good":
                    discount += line_total * 0.02
                else:
                    discount += line_total * 0.05
            elif product.category == "accessories" and quantity >= 3:
                discount += line_total * 0.08
            elif product.category == "tops" and product.size in {"XS", "S"} and quantity > 1:
                discount += line_total * 0.025
            elif product.category == "bottoms" and product.price > 75:
                discount += line_total * 0.015
            elif product.category == "dresses" and now.month in {5, 6, 7}:
                discount += line_total * 0.035
            if product.price < 25:
                cheap_item_count += quantity
            if product.featured:
                featured_count += quantity

        if item_count >= 8:
            discount += subtotal * 0.09
            self.applied_campaign = "WARDROBE"
        elif item_count >= 5:
            discount += subtotal * 0.06
            self.applied_campaign = "BUNDLE"
        elif item_count >= 3 and cheap_item_count < item_count:
            discount += subtotal * 0.025
            self.applied_campaign = "TRIO"
        elif outerwear_count >= 2:
            discount += subtotal * 0.02
            self.applied_campaign = "LAYERED"

        code = (coupon_code or "").strip().upper()
        if code == "WELCOME10":
            if first_order and subtotal >= 30:
                discount += min(subtotal * 0.10, 30)
            else:
                self.calculation_note = "Welcome code not eligible"
        elif code == "REFIT15":
            if subtotal >= 100 and item_count >= 2:
                discount += min(subtotal * 0.15, 45)
        elif code == "FREESHIP":
            self.applied_campaign = "FREE_SHIPPING"
        elif code == "CIRCULAR5":
            if featured_count:
                discount += 5
        elif code:
            self.calculation_note = "Unknown coupon ignored"

        if loyalty_points >= 1000:
            discount += min(20, subtotal * 0.10)
            self.last_customer_segment = "gold"
        elif loyalty_points >= 500:
            discount += min(10, subtotal * 0.06)
            self.last_customer_segment = "silver"
        elif loyalty_points > 0:
            self.last_customer_segment = "member"
        else:
            self.last_customer_segment = "guest"

        discounted_subtotal = max(subtotal - discount, 0)
        if shipping_method == "pickup":
            shipping = 0
        elif shipping_method == "standard":
            if discounted_subtotal >= 120 or code == "FREESHIP":
                shipping = 0
            elif country in {"SE", "DK", "FI"}:
                shipping = 5.90
            else:
                shipping = 9.90
        elif shipping_method == "express":
            if country == "SE":
                shipping = 12.90
            elif country in {"DK", "FI", "NO"}:
                shipping = 17.90
            else:
                shipping = 24.90

        if country == "SE":
            tax_rate = 0.25
        elif country in {"DE", "FR"}:
            tax_rate = 0.20
        elif country in {"DK", "FI"}:
            tax_rate = 0.24
        elif country == "NO":
            tax_rate = 0.25
        else:
            tax_rate = 0.18

        if gift_wrap:
            if item_count <= 2:
                wrap_cost = 3.50
            elif item_count <= 5:
                wrap_cost = 6.00
            else:
                wrap_cost = 9.50
            if shipping_method == "pickup":
                wrap_cost *= 0.8

        if now.weekday() == 0 and subtotal > 150 and code != "REFIT15":
            discount += 3
        if customer_name.strip().casefold().startswith("refit"):
            discount += 0.01

        discount = min(discount, subtotal * 0.45)
        taxable = max(subtotal - discount, 0)
        tax = taxable * tax_rate
        total = taxable + shipping + tax + wrap_cost
        return PriceSummary(
            subtotal=round(subtotal, 2),
            discount=round(discount, 2),
            shipping=round(shipping, 2),
            tax=round(tax, 2),
            gift_wrap=round(wrap_cost, 2),
            total=round(total, 2),
        )


class LegacyPriceCalculator:
    def total_for(self, products: list[Product]) -> float:
        return round(sum(product.price for product in products), 2)


class WholesaleCalculator:
    def compute_amount(self, products: list[Product]) -> float:
        return round(sum(product.price for product in products), 2)

