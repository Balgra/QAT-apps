from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4

from fastapi import HTTPException

from .models import Product


def cents(value):
    return int((Decimal(str(value)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


class ReceiptRecord:
    def __init__(self, payload):
        self.payload = payload

    def as_dict(self):
        return self.payload


class CommerceService:
    def __init__(self, repository, pricing, clock=None):
        self.repository = repository
        self.pricing = pricing
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.active_return = None
        self.review_reason = None
        self.last_payout = None

    def _expire(self, state):
        for reservation in state["reservations"].values():
            if reservation["status"] == "held" and datetime.fromisoformat(reservation["expires_at"]) <= self.clock():
                reservation["status"] = "expired"

    def _lines(self, state, request):
        self._expire(state)
        own = state["reservations"].get(request.reservation_id) if request.reservation_id else None
        if request.reservation_id:
            if not own or own["status"] != "held":
                raise HTTPException(409, "Reservation has expired or is unavailable")
            if own["email"] != request.email.casefold():
                raise HTTPException(409, "Reservation belongs to another shopper")
            if own["items"] != [item.model_dump() for item in request.items]:
                raise HTTPException(409, "Cart differs from the reserved cart")
        seen = set()
        lines = []
        for item in request.items:
            if item.product_id in seen:
                raise HTTPException(400, "Duplicate cart line")
            seen.add(item.product_id)
            row = next((p for p in state["products"] if p["id"] == item.product_id), None)
            if row is None:
                raise HTTPException(404, "Product not found")
            if state["moderation"].get(str(item.product_id), {}).get("status") == "rejected":
                raise HTTPException(409, "Listing is unavailable")
            held = sum(line["quantity"] for key, hold in state["reservations"].items()
                       if hold["status"] == "held" and key != request.reservation_id
                       for line in hold["items"] if line["product_id"] == item.product_id)
            if item.quantity > row["stock"] - held:
                raise HTTPException(409, f"Insufficient available stock for {row['name']}")
            if row["condition"] == "fair" and item.quantity > 1:
                raise HTTPException(400, "Fair-condition pieces are limited to one")
            lines.append((Product.model_validate(row), item.quantity))
        return lines

    def _quote(self, state, request):
        lines = self._lines(state, request)
        country = request.country.upper()
        messages = []
        if country not in {"SE", "DK", "FI", "NO", "DE", "FR", "US"}:
            raise HTTPException(400, "Delivery is unavailable in this region")
        if request.shipping_method == "pickup":
            if country != "SE":
                raise HTTPException(400, "Studio pickup is available only in Sweden")
            messages.append("Collect from the Gothenburg studio")
        elif request.shipping_method == "express":
            if country == "US":
                raise HTTPException(400, "Express delivery is unavailable to the US")
            if any(p.category == "outerwear" and p.condition == "fair" for p, _ in lines):
                messages.append("Condition check included before express dispatch")
            else:
                messages.append("Express delivery selected")
        else:
            messages.append("Standard delivery selected")
        profile = state["profiles"].get(request.email.casefold(), {"points": 0, "first_order": True})
        totals = self.pricing.calculate(lines, request.shipping_method, request.coupon_code,
                                        request.gift_wrap, country, request.customer_name,
                                        self.clock(), profile["points"], profile["first_order"])
        code = (request.coupon_code or "").strip().upper()
        if code == "WELCOME10":
            if profile["first_order"] and totals.subtotal >= 30:
                messages.append("Welcome discount applied")
            else:
                messages.append("Welcome discount requires a first order of at least EUR 30")
        elif code == "REFIT15":
            if totals.subtotal >= 100 and sum(q for _, q in lines) >= 2:
                messages.append("REFIT15 campaign applied")
            else:
                messages.append("REFIT15 requires two items and EUR 100 subtotal")
        elif code == "CIRCULAR5":
            messages.append("Featured-piece coupon" if any(p.featured for p, _ in lines) else "Coupon requires a featured piece")
        elif code == "FREESHIP":
            messages.append("Free standard shipping; express prices are unchanged")
        elif code:
            messages.append("Unknown coupon ignored")
        if profile["points"] >= 1000:
            messages.append("Gold member pricing")
        elif profile["points"] >= 500:
            messages.append("Silver member pricing")
        else:
            messages.append("Guest pricing")
        # Round each displayed component before combining the receipt.
        totals.total = round(totals.subtotal - totals.discount + totals.shipping + totals.tax + totals.gift_wrap, 2)
        return {"totals": totals.model_dump(), "messages": messages, "contract_version": "2"}, lines

    def quote(self, request):
        with self.repository.store.lock:
            return self._quote(self.repository.store.read(), request)[0]

    def purchase(self, request):
        with self.repository.store.transaction() as state:
            quote, lines = self._quote(state, request)
            totals = quote["totals"]
            rows = []
            discount_left = cents(totals["discount"])
            tax_left = cents(totals["tax"])
            for index, (product, quantity) in enumerate(lines):
                gross = cents(product.price) * quantity
                if index == len(lines) - 1:
                    discount = discount_left
                    tax = tax_left
                else:
                    discount = min(discount_left, round(cents(totals["discount"]) * gross / cents(totals["subtotal"])))
                    tax = min(tax_left, round(cents(totals["tax"]) * gross / cents(totals["subtotal"])))
                discount_left -= discount
                tax_left -= tax
                rows.append({"product": product.model_dump(), "quantity": quantity, "returned": 0,
                             "paid_cents": gross - discount + tax, "refunded_cents": 0,
                             "discount_cents": discount, "tax_cents": tax})
                next(p for p in state["products"] if p["id"] == product.id)["stock"] -= quantity
            order_id = "RF-" + uuid4().hex[:10].upper()
            order = {"order_id": order_id, "status": "placed", "created_at": self.clock().isoformat(),
                     "email": request.email.casefold(), "country": request.country.upper(), "lines": rows,
                     "totals": totals, "returns": {}, "refunded": 0, "delivered_at": None,
                     "item_count": sum(q for _, q in lines), "contract_version": "2"}
            state["orders"][order_id] = order
            state["profiles"].setdefault(request.email.casefold(), {"points": 0, "first_order": True})["first_order"] = False
            if request.reservation_id:
                state["reservations"][request.reservation_id]["status"] = "consumed"
        return {"order_id": order_id, "message": "Thank you for giving great clothes another story.",
                "totals": totals, "item_count": order["item_count"]}

    def list_orders(self):
        orders = self.repository.store.read()["orders"].values()
        return [{"order_id": order["order_id"], "created_at": order["created_at"],
                 "status": order["status"], "total": order["totals"]["total"],
                 "item_count": order["item_count"]}
                for order in sorted(orders, key=lambda row: (datetime.fromisoformat(row["created_at"]), row["order_id"]), reverse=True)]

    def get_order(self, order_id):
        order = self.repository.store.read()["orders"].get(order_id)
        if not order:
            raise HTTPException(404, "Order not found")
        return ReceiptRecord(order).as_dict()

    def cancel_order(self, order_id):
        with self.repository.store.transaction() as state:
            order = state["orders"].get(order_id)
            if order is None:
                raise HTTPException(404, "Order not found")
            if order["status"] == "cancelled":
                return order
            if order["status"] == "placed":
                for line in order["lines"]:
                    product = next((p for p in state["products"] if p["id"] == line["product"]["id"]), None)
                    if product:
                        if product["stock"] + line["quantity"] > 100:
                            raise HTTPException(409, "Stock capacity would be exceeded")
                        product["stock"] += line["quantity"]
                    else:
                        raise HTTPException(409, "Original listing must exist to cancel")
                order["status"] = "cancelled"
                order["refunded"] = order["totals"]["total"]
            elif order["status"] == "dispatched":
                raise HTTPException(409, "Dispatched orders cannot be cancelled")
            elif order["status"] == "delivered":
                raise HTTPException(409, "Delivered orders require a return")
            elif order["status"] in {"partially-returned", "returned"}:
                raise HTTPException(409, "Returned orders cannot be cancelled")
            else:
                raise HTTPException(409, "Order state does not support cancellation")
        return order

    def transition(self, order_id, status):
        with self.repository.store.transaction() as state:
            order = state["orders"].get(order_id)
            if not order:
                raise HTTPException(404, "Order not found")
            allowed = {"placed": "dispatched", "dispatched": "delivered"}
            if order["status"] == status:
                return order
            if allowed.get(order["status"]) != status:
                raise HTTPException(409, "Invalid order transition")
            order["status"] = status
            if status == "delivered":
                order["delivered_at"] = self.clock().isoformat()
        return order

    def evaluate_return(self, order_id, request):
        with self.repository.store.transaction() as state:
            order = state["orders"].get(order_id)
            if not order:
                raise HTTPException(404, "Order not found")
            previous = order["returns"].get(request.request_id)
            if previous:
                if previous["request"] != request.model_dump():
                    raise HTTPException(409, "Return reference already used for different details")
                return previous
            if order["status"] not in {"delivered", "partially-returned"}:
                raise HTTPException(409, "Only delivered items can be returned")
            line = next((r for r in order["lines"] if r["product"]["id"] == request.product_id), None)
            if not line:
                raise HTTPException(404, "Item is not part of this order")
            age = self.clock() - datetime.fromisoformat(order["delivered_at"])
            if age < timedelta(0):
                raise HTTPException(409, "Delivery time is in the future")
            if request.reason in {"damaged", "wrong-item"}:
                if age > timedelta(days=30):
                    raise HTTPException(400, "Issue-report window is 30 days")
                if request.condition == "worn" and request.reason == "wrong-item":
                    raise HTTPException(400, "Wrong-item returns must not be worn")
            elif request.reason == "fit":
                if age > timedelta(days=14):
                    raise HTTPException(400, "Fit returns are limited to 14 days")
                if request.condition == "worn":
                    raise HTTPException(400, "Worn items cannot be returned for fit")
            elif request.reason == "changed-mind":
                if age > timedelta(days=14):
                    raise HTTPException(400, "Change-of-mind window is 14 days")
                if request.condition != "unworn":
                    raise HTTPException(400, "Change-of-mind returns must be unworn")
                if line["product"]["condition"] == "fair":
                    raise HTTPException(400, "Fair-condition items only support fit or fault returns")
            if request.quantity > line["quantity"] - line["returned"]:
                raise HTTPException(409, "Return quantity exceeds remaining purchased quantity")
            new_returned = line["returned"] + request.quantity
            cumulative = line["paid_cents"] * new_returned // line["quantity"]
            refund = cumulative - line["refunded_cents"]
            line["returned"] = new_returned
            line["refunded_cents"] = cumulative
            product = next((p for p in state["products"] if p["id"] == request.product_id), None)
            if request.condition == "unworn" and request.reason not in {"damaged", "wrong-item"}:
                if product and product["stock"] + request.quantity <= 100:
                    product["stock"] += request.quantity
            order["refunded"] = round(order["refunded"] + refund / 100, 2)
            order["status"] = "returned" if all(r["returned"] == r["quantity"] for r in order["lines"]) else "partially-returned"
            self.active_return = {"request": request.model_dump(), "refund": refund / 100,
                                  "status": "approved", "created_at": self.clock().isoformat()}
            order["returns"][request.request_id] = self.active_return
        return self.active_return

    def reserve(self, request):
        from .models import QuoteRequest
        with self.repository.store.transaction() as state:
            self._lines(state, QuoteRequest(items=request.items, email=request.email))
            key = "HOLD-" + uuid4().hex[:8]
            hold = {"reservation_id": key, "email": request.email.casefold(), "status": "held",
                    "expires_at": (self.clock() + timedelta(minutes=10)).isoformat(),
                    "items": [i.model_dump() for i in request.items]}
            state["reservations"][key] = hold
        return hold

    def release(self, key):
        with self.repository.store.transaction() as state:
            hold = state["reservations"].get(key)
            if not hold:
                raise HTTPException(404, "Reservation not found")
            if hold["status"] == "held":
                hold["status"] = "released"
        return hold

    def seller_summary(self, seller):
        state = self.repository.store.read()
        tier = state["sellers"].get(seller, {}).get("tier", "standard")
        gross = 0
        commission = 0
        pending_gross = 0
        pending_commission = 0
        for order in state["orders"].values():
            if order["status"] == "cancelled":
                continue
            for line in order["lines"]:
                if line["product"]["seller"] != seller:
                    continue
                net = line["paid_cents"] - line["refunded_cents"]
                if tier == "trusted":
                    if line["product"]["category"] == "outerwear":
                        rate = Decimal("0.06")
                    else:
                        rate = Decimal("0.07")
                elif tier == "standard":
                    if line["product"]["category"] in {"shoes", "accessories"}:
                        rate = Decimal("0.12")
                    else:
                        rate = Decimal("0.10")
                else:
                    rate = Decimal("0.15")
                fee = int((Decimal(net) * rate).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
                if order["status"] in {"placed", "dispatched"}:
                    pending_gross += net
                    pending_commission += fee
                else:
                    gross += net
                    commission += fee
        self.last_payout = {"seller": seller, "tier": tier, "gross": gross / 100,
                            "commission": commission / 100, "payout": (gross - commission) / 100,
                            "pending_sales": pending_gross / 100, "pending_commission": pending_commission / 100,
                            "pending_payout": (pending_gross - pending_commission) / 100,
                            "total_sales": (gross + pending_gross) / 100,
                            "estimated_earnings": (gross + pending_gross - commission - pending_commission) / 100}
        return self.last_payout

    def moderate(self, product_id, request):
        with self.repository.store.transaction() as state:
            product = next((p for p in state["products"] if p["id"] == product_id), None)
            if not product:
                raise HTTPException(404, "Product not found")
            seller = state["sellers"].setdefault(product["seller"], {"tier": "standard", "reviews": 0, "rejections": 0})
            reasons = []
            if product["price"] > 500:
                if seller["tier"] != "trusted":
                    reasons.append("High-value item requires review")
            if product["condition"] == "fair":
                if len(product["description"]) < 40:
                    reasons.append("Fair-condition listing needs a fuller description")
            if product["stock"] > 20:
                reasons.append("Volume exceeds individual-seller threshold")
            if seller["rejections"] >= 3:
                reasons.append("Seller requires manual approval")
            if request.action == "approve":
                status = "approved"
                seller["reviews"] += 1
                if seller["reviews"] >= 3 and seller["rejections"] == 0:
                    seller["tier"] = "trusted"
            elif request.action == "reject":
                status = "rejected"
                seller["rejections"] += 1
                if seller["rejections"] >= 3:
                    seller["tier"] = "restricted"
            else:
                status = "pending" if reasons else "approved"
            result = {"status": status, "reasons": reasons, "note": request.note, "seller": seller.copy()}
            state["moderation"][str(product_id)] = result
            self.review_reason = reasons or None
        return result
