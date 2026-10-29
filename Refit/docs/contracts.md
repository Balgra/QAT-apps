# Refit behavior and client contracts

## Local service

FastAPI exposes `/api` on port 8000. In Docker, the browser uses `/api` on port 5173 and Nginx proxies it to `backend:8000`. The default API is a local teaching service; seller and fulfilment controls have no separate authentication.

Every normal backend launch copies `backend/data/products.json` into a temporary session directory. Orders and other changes remain available while that backend process runs, including after browser refresh. A new backend process starts from the supplied catalog again; the original file is unchanged. Explicit file paths passed to the application factory remain available for isolated repository/persistence tests.

## Checkout

`POST /api/quote` accepts the same order fields as checkout but does not require payment fields. `POST /api/checkout` additionally requires a Luhn-valid card number, a non-expired `MM/YY`, and 3-4 digit CVV.

```json
{
  "items": [{"product_id": 2, "quantity": 1}],
  "customer_name": "Demo Customer",
  "email": "guest@example.com",
  "address": "Example Street 12",
  "city": "Gothenburg",
  "postal_code": "41257",
  "country": "SE",
  "shipping_method": "standard",
  "coupon_code": "WELCOME10",
  "gift_wrap": false,
  "card_number": "4242424242424242",
  "expiry": "12/35",
  "cvv": "123"
}
```

Quotes return `contract_version: "2"`, numeric `totals`, and eligibility `messages`. Purchase returns `order_id`, `totals`, `item_count`, and `message`. All money is EUR. Card details are never saved. The server derives profile points from the email; a client-supplied points value does not change membership.

Delivery values are trimmed before checkout validation; country codes are converted to uppercase. Name and city must contain letters and be 2–80 characters long. Address must contain letters and a number and be 5–180 characters long (for example, `Example Street 12` or `PO Box 12`). Email must have the documented `name@example.com` shape. These checks validate format only; there is no external address, identity, or mailbox verification.

| Country | Accepted postal format |
| --- | --- |
| SE | Five ASCII digits, optionally separated after the third digit: `41257` or `412 57` |
| DK, NO | Four ASCII digits, preserving leading zeros |
| FI, DE, FR | Five ASCII digits, preserving leading zeros |
| US | Five ASCII digits, optionally followed by a hyphen and four digits: `10001` or `10001-1234` |

Invalid checkout input returns HTTP 422 with the affected field in `detail[].loc`. No stock or order changes occur. The React checkout displays inline errors on blur and submission, focuses the first invalid input, and preserves entered values. General server failures focus an error summary. Invalid client-side input sends no purchase request.

## Pricing policy

Product prices exclude tax. Calculations use the same backend routine for quotes and purchases. Displayed components are rounded to two decimals using Python rounding, and the final total is the sum of those components. Original line refunds/commission allocations use integer cents, with rounding residue assigned to the final line. Fractional partial refunds accumulate against original paid cents and reconcile on the final return.

| Stage | Rule |
| --- | --- |
| Per-line reductions | Fair outerwear 4%; good outerwear with quantity >= 2 gets 3%. Shoes: new 0%, like-new 1%, good 2%, fair 5%. Accessories quantity >= 3 get 8%; XS/S tops quantity > 1 get 2.5%; bottoms priced above 75 get 1.5%; dresses in May-July get 3.5%. |
| Quantity campaign | First matching rule: >= 8 pieces 9%; >= 5 pieces 6%; >= 3 pieces with at least one piece priced >= 25 gets 2.5%; otherwise >= 2 outerwear pieces get 2%. |
| Optional coupon | One case-insensitive code: WELCOME10 gives 10% capped at 30 for first order and subtotal >= 30; REFIT15 gives 15% capped at 45 for subtotal >= 100 and at least two pieces; CIRCULAR5 deducts 5 when a featured piece is present. Unknown/ineligible codes have no monetary effect. |
| Membership | >= 1,000 stored points: 10% capped at 20; >= 500 points: 6% capped at 10. Profiles are stored demo fixtures; a successful purchase clears first-order eligibility for its email. |
| Delivery | Pickup: SE only and free. Standard: free when discounted subtotal >= 120 or coupon FREESHIP; otherwise 5.90 in SE/DK/FI and 9.90 elsewhere. Express: 12.90 in SE, 17.90 in DK/FI/NO, 24.90 in DE/FR. US has standard delivery only. Other regions are rejected. |
| Gift wrap | 1-2 pieces 3.50; 3-5 pieces 6; >= 6 pieces 9.50. Pickup reduces wrap cost by 20%. |
| Final discount adjustments | Monday subtotal > 150 adds 3 except with REFIT15. Customer names beginning with `refit` receive a 0.01 demonstration adjustment. Combined discount capped at 45% of subtotal. Shipping eligibility is evaluated before these final adjustments. |
| Tax | On discounted merchandise only: SE/NO 25%, DE/FR 20%, DK/FI 24%, US 18%. These are fixed exercise values. Delivery and wrapping receive no additional tax. |

## Order and inventory operations

| Operation | Endpoint and policy |
| --- | --- |
| List orders | `GET /api/orders`; returns all saved local-demo orders newest first, including cancelled and returned orders. Each summary includes `order_id`, `created_at`, `status`, `total`, and `item_count`. An empty shop returns `[]`. There are no user accounts or per-user filtering. |
| Read order | `GET /api/orders/{order_id}`; returns original line snapshots and return history within the current backend run. |
| Cancel | `POST /api/orders/{order_id}/cancel`; only placed orders; refund complete total and restore quantities once. Repeating cancellation returns the cancelled order. |
| Fulfilment | `PATCH /api/orders/{order_id}/status` with `{"status":"dispatched"}` then `{"status":"delivered"}`. Delivery records server time. Repeating the current transition is harmless. |
| Return | `POST /api/orders/{order_id}/returns` with `product_id`, `quantity`, `reason`, `condition`, and a unique `request_id`. Same reference/same payload returns the earlier result; a changed payload under the same reference is rejected. |
| Return window | Fit and changed-mind: <= 14 elapsed days after delivery; damaged/wrong-item: <= 30 days. Exact deadline is inclusive. Returns require delivered/partially-returned state. |
| Return condition | Fit allows unworn/opened. Changed-mind requires unworn and excludes originally fair-condition pieces. Wrong-item rejects worn pieces; damaged returns accept any condition. |
| Refund | Original discounted merchandise plus allocated tax only; delivery/wrapping retained. Partial refunds cannot exceed original purchased quantity/paid cents. Unworn non-fault returns replenish an existing listing when stock capacity permits. |
| Reserve | `POST /api/reservations` with `items` and `email`; holds available units for exactly ten minutes. Supply returned `reservation_id` to quote/checkout with identical items/email. `DELETE /api/reservations/{id}` releases an unused hold. Expiry is checked at operation time. |
| State safety | One worker/process, one JSON file, in-process lock and atomic replacement. No claim of coordination between separate processes writing the same file. |

## Seller operations

`GET /api/sellers/{seller}/summary` reports sales and earnings using original paid merchandise/tax allocations less refunded amounts; shipping and wrapping are excluded. Cancelled orders are excluded. Rates: standard seller 10% except shoes/accessories 12%; trusted seller 6% outerwear, 7% otherwise; restricted seller 15%. It is a recomputed estimate using the current seller tier, not a bank transfer or settlement ledger.

| Summary field | Meaning |
| --- | --- |
| `gross`, `commission`, `payout` | Delivered/partially-returned/returned sales after refunds, associated commission, and available payout estimate. These existing fields retain their original semantics. |
| `pending_sales`, `pending_commission`, `pending_payout` | The same breakdown for placed/dispatched orders awaiting delivery. |
| `total_sales` | Delivered plus pending sales after refunds. |
| `estimated_earnings` | Available plus pending payout estimates, after commission. |

For example, a new standard-seller tops order with EUR 100 merchandise plus EUR 25 allocated tax immediately shows EUR 125 sales and EUR 112.50 pending earnings. Delivery moves that EUR 112.50 to the available estimate. A full return reduces those sales and earnings to zero. No status transition is required to see a newly placed sale.

The studio loads the saved order and its first seller on opening. Each order line identifies its seller, including mixed-seller orders. The selected seller summary loads automatically, refreshes after order changes, and can be refreshed manually.

`POST /api/products/{id}/moderation` accepts action `review`, `approve`, or `reject`, and optional `note`. Automatic review flags price > 500 for non-trusted sellers, fair items with description length < 40, stock > 20, or sellers with >= 3 rejections. Rejected listings cannot be bought. Three approvals without rejections make a seller trusted; three rejections make them restricted. Operator decisions update the stored status/reputation and can override review advice.

The supplied demo catalog has five sellers (Mira, Linnea, Noah, Elias, Ava), four listings each, and 20 listings in total with varied quantities. Seller names on existing demo receipt lines have been reassigned consistently with their listings; saved order references, financial amounts, stock, and status are retained. Product CRUD remains available for student exercises and does not impose a five-seller limit on new listings.
