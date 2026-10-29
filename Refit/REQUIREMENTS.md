# Refit requirements

## Product description

Refit is a browser-based marketplace for buying pre-owned clothing from individual sellers. The React client communicates with a FastAPI service over HTTP. Product records are persisted in a local JSON-backed mock database. Payment is a demonstration only and must never contact a real payment provider.

## Functional requirements

- **FR-01 — Browse catalog:** The system shall show all available clothing listings with name, category, size, condition, seller, price, colour, stock state, and featured state. The supplied demo catalog shall contain 20 listings, four each for Mira, Linnea, Noah, Elias, and Ava, with varied initial quantities.
- **FR-02 — Search catalog:** A shopper shall be able to search listings by product name, description, or seller.
- **FR-03 — Filter catalog:** A shopper shall be able to filter listings by clothing category and return to an all-categories view.
- **FR-04 — View stock:** The storefront shall prevent adding a sold-out listing to the cart.
- **FR-05 — Add to cart:** A shopper shall be able to add an available product to the cart.
- **FR-06 — Edit cart:** A shopper shall be able to increase or decrease each cart quantity without exceeding available stock; reducing a quantity below one shall remove the line.
- **FR-07 — Review cart:** The cart shall show selected products, quantities, line totals, and estimated subtotal.
- **FR-08 — Enter delivery details:** Checkout shall collect the shopper's name, email, address, city, postal code, and two-letter country code. Names and cities shall contain letters; a street or PO box address shall contain letters and a number. Email syntax, supported country codes, and country-specific postal formats shall be validated before purchase.
- **FR-09 — Select delivery:** Checkout shall support standard delivery, express delivery, and pickup.
- **FR-10 — Enter demonstration payment:** Checkout shall accept a syntactically valid card number, future expiry, and three- or four-digit CVV; it shall apply a checksum validation without making a real payment.
- **FR-11 — Price order:** The backend shall calculate subtotal, applicable discounts, delivery, tax, optional gift wrapping, and final total.
- **FR-12 — Apply coupon:** Checkout shall accept an optional coupon code and apply it only when its eligibility conditions are satisfied.
- **FR-13 — Complete order:** A valid order shall reduce inventory and return an order identifier, item count, complete price summary, and thank-you message.
- **FR-14 — Reject invalid order:** The service shall reject missing products, duplicate cart lines, invalid payment details, sold-out items, and quantities above stock without changing inventory.
- **FR-15 — Manage products:** The backend shall provide operations to create, retrieve, list, partially update, and delete products.
- **FR-16 — Query products:** The product-list operation shall accept optional category and free-text query parameters.
- **FR-17 — Service health:** The backend shall expose a health endpoint suitable for an automated availability check.
- **FR-18 — Quote:** A shopper shall be able to request a final quote and eligibility explanations before purchase; the same inputs, time, stock, and profile shall produce the same quote and checkout total.
- **FR-19 — Membership:** The backend shall derive coupon eligibility and member reductions from stored demonstration profiles and completed purchase history.
- **FR-20 — Order history:** During the current backend run, a shopper shall be able to select any saved order from a dropdown showing its reference, date, total, and status, newest first, and retrieve the original receipt, purchased line prices, status, and return history. Refreshing the browser shall preserve the current run's orders. With no saved orders, the interface shall explain that purchases will appear after checkout and disable order lookup.
- **FR-21 — Cancellation:** A placed order shall be cancellable with its full original total refunded and inventory restored once. Cancellation after dispatch shall be rejected.
- **FR-22 — Fulfilment:** A demonstration operator shall be able to progress placed orders to dispatched and then delivered; delivery time shall be recorded.
- **FR-23 — Returns:** A shopper shall be able to request full or partial returns within the documented fit/change-of-mind or fault-report window, subject to condition and purchased-quantity checks.
- **FR-24 — Refund:** Approved returns shall use original paid merchandise and allocated tax; delivery and wrapping shall be retained. Retrying the same return reference shall not issue another refund.
- **FR-25 — Reservations:** A shopper shall be able to hold a cart for ten minutes, consume the hold at purchase, or release it; expired holds shall no longer reduce availability.
- **FR-26 — Seller summary:** A seller shall be able to view sales and estimated earnings immediately after purchase, with separate pending earnings for placed/dispatched orders and available payout estimates for delivered orders. The summary shall show commissions, exclude cancellations, and reduce earnings after refunds under the documented tier/category policy. It shall load automatically when the seller changes and refresh after order actions; retrieved order lines shall identify their sellers.
- **FR-27 — Listing review:** An operator shall be able to review, approve, or reject listings; rejected listings shall be unavailable for purchase and decisions shall update seller reputation.
- **FR-28 — Regional delivery:** The backend shall enforce the documented country, express-delivery, and studio-pickup restrictions with a clear rejection for unsupported choices.

## Non-functional requirements

- **NFR-01 — Usability:** A first-time shopper shall be able to browse, add a product, and reach checkout without instructions outside the interface.
- **NFR-02 — Responsiveness:** The storefront shall remain usable from a 320-pixel-wide viewport through desktop widths.
- **NFR-03 — Accessibility:** Interactive elements shall be keyboard operable, form inputs shall have labels, dialogs shall expose appropriate roles, and information shall not depend solely on colour.
- **NFR-04 — Feedback:** Loading, empty, failure, validation, and successful-order states shall be visible to the shopper. Invalid checkout fields shall have explanatory inline messages; submission shall focus the first invalid field, preserve entered values, and block purchase. Server validation errors shall identify the corresponding fields; other checkout failures shall focus a visible error summary.
- **NFR-05 — Integrity:** Successful orders shall persist stock changes; rejected orders shall not change stored stock.
- **NFR-06 — Validation:** The API shall validate request types, string lengths, numeric bounds, and allowed enumerated values before processing.
- **NFR-07 — Portability:** The application shall run locally on current Python and Node.js versions using the documented commands.
- **NFR-08 — Testability:** Backend creation shall support an alternate catalog path so automated tests can use isolated data.
- **NFR-09 — Inspectability:** API operations shall be discoverable through generated OpenAPI documentation.
- **NFR-10 — Privacy:** Card input shall be used only for local demonstration validation and shall not be persisted.
- **NFR-11 — Maintainable contract:** Behaviour documented here shall remain stable during analysis and refactoring exercises.
- **NFR-12 — Performance:** With the supplied catalog, product-list and product-detail responses should complete within one second on a typical development machine.
- **NFR-13 — Atomic persistence:** Within a single backend process, stock and order changes shall commit together; a failed persistence operation shall preserve the previous state.
- **NFR-14 — Compatibility:** Current and previous documented client contracts shall exchange cart, delivery, coupon, and total information correctly in 100% of valid compatibility acceptance cases. This is the target assessed by the README quality scenario.
- **NFR-15 — Reproducibility:** Tests shall use isolated fixture data and controllable time for return windows and reservation expiry.
- **NFR-16 — Fresh startup:** Each new backend process shall begin with the supplied catalog, quantities, and demo profiles, with no orders or reservations from a previous run. Normal use shall not change the supplied data file.

## Additional student implementation use cases

### UC-05 — Review, reserve, and buy

**Actor:** Shopper. **Preconditions:** Available cart and delivery information.

1. The shopper requests a quote and reviews its total and eligibility messages.
2. The shopper optionally reserves the pieces for ten minutes.
3. The shopper buys using the same email/cart or releases the hold.

**Alternatives:** Changed or expired reservations, unsupported delivery, and insufficient stock receive a rejection. **Postcondition:** A successful purchase stores the receipt and consumes stock once.

### UC-06 — Follow, cancel, or return an order

**Actor:** Shopper; operator for dispatch/delivery simulation. **Precondition:** Known order reference.

1. The shopper retrieves the receipt through Orders / seller studio.
2. Before dispatch, the shopper may cancel the order.
3. The operator marks a fulfilled order dispatched and delivered.
4. The shopper selects purchased pieces, quantities, a reason, and condition to request a return.

**Alternatives:** Ineligible status, expired window, worn condition, or excess quantity is rejected. **Postcondition:** Only eligible refunds/restocking occur; repeated references preserve the earlier result.

### UC-07 — Review listings and seller proceeds

**Actor:** Seller or demonstration catalog operator. **Precondition:** Existing seller/listing.

1. The operator requests a listing review and records an approval or rejection.
2. The seller requests the proceeds summary after deliveries and returns.

**Postcondition:** Listing availability/reputation reflects the decision; payout estimates reflect commissions and recorded refunds.

## Student implementation use cases

### UC-01 — Explore the wardrobe

**Actor:** Shopper  
**Goal:** Find a suitable pre-owned garment.  
**Precondition:** The frontend and backend are running.

**Main flow:**

1. The shopper opens Refit.
2. The system loads the catalog.
3. The shopper searches or selects a category.
4. The system immediately narrows the visible products.
5. The shopper reviews item details and availability.

**Alternative:** If the API is unavailable, the system explains that the wardrobe could not be loaded.

### UC-02 — Prepare an order

**Actor:** Shopper  
**Goal:** Assemble and review a cart.  
**Precondition:** At least one product has stock.

**Main flow:**

1. The shopper quick-adds a product.
2. The system opens the cart and shows a quantity of one.
3. The shopper adjusts quantities or adds more products.
4. The system keeps quantities within stock and recalculates line totals and subtotal.
5. The shopper proceeds to checkout.

### UC-03 — Buy the selected clothes

**Actor:** Shopper  
**Goal:** Complete a demonstration purchase.  
**Precondition:** The cart is not empty.

**Main flow:**

1. The shopper provides delivery details.
2. The shopper chooses a delivery method and optionally adds gift wrapping or a coupon.
3. The shopper enters demonstration-card details and selects **Buy now**.
4. The backend validates the cart and card, calculates the order, and updates stock.
5. The system displays a thank-you confirmation, order ID, item count, and final total.

**Alternatives:** Invalid card or order information produces a useful error; changed stock produces a conflict response and no inventory update.

### UC-04 — Maintain the catalog through the API

**Actor:** Catalog operator  
**Goal:** Keep product listings accurate.  
**Precondition:** The API is running.

**Main flow:**

1. The operator creates or selects a product through the documented API.
2. The API validates the supplied product information.
3. The operator retrieves, partially updates, or deletes the listing.
4. The JSON-backed catalog persists the successful change.

