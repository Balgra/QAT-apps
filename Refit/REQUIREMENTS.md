# Refit requirements

## Product description

Refit is a browser-based marketplace for buying pre-owned clothing from individual sellers. The React client communicates with a FastAPI service over HTTP. Product records are persisted in a local JSON-backed mock database. Payment is a demonstration only and must never contact a real payment provider.

## Functional requirements

- **FR-01 — Browse catalog:** The system shall show all available clothing listings with name, category, size, condition, seller, price, colour, stock state, and featured state.
- **FR-02 — Search catalog:** A shopper shall be able to search listings by product name, description, or seller.
- **FR-03 — Filter catalog:** A shopper shall be able to filter listings by clothing category and return to an all-categories view.
- **FR-04 — View stock:** The storefront shall prevent adding a sold-out listing to the cart.
- **FR-05 — Add to cart:** A shopper shall be able to add an available product to the cart.
- **FR-06 — Edit cart:** A shopper shall be able to increase or decrease each cart quantity without exceeding available stock; reducing a quantity below one shall remove the line.
- **FR-07 — Review cart:** The cart shall show selected products, quantities, line totals, and estimated subtotal.
- **FR-08 — Enter delivery details:** Checkout shall collect the shopper's name, email, address, city, postal code, and two-letter country code.
- **FR-09 — Select delivery:** Checkout shall support standard delivery, express delivery, and pickup.
- **FR-10 — Enter demonstration payment:** Checkout shall accept a syntactically valid card number, future expiry, and three- or four-digit CVV; it shall apply a checksum validation without making a real payment.
- **FR-11 — Price order:** The backend shall calculate subtotal, applicable discounts, delivery, tax, optional gift wrapping, and final total.
- **FR-12 — Apply coupon:** Checkout shall accept an optional coupon code and apply it only when its eligibility conditions are satisfied.
- **FR-13 — Complete order:** A valid order shall reduce inventory and return an order identifier, item count, complete price summary, and thank-you message.
- **FR-14 — Reject invalid order:** The service shall reject missing products, duplicate cart lines, invalid payment details, sold-out items, and quantities above stock without changing inventory.
- **FR-15 — Manage products:** The backend shall provide operations to create, retrieve, list, partially update, and delete products.
- **FR-16 — Query products:** The product-list operation shall accept optional category and free-text query parameters.
- **FR-17 — Service health:** The backend shall expose a health endpoint suitable for an automated availability check.

## Non-functional requirements

- **NFR-01 — Usability:** A first-time shopper shall be able to browse, add a product, and reach checkout without instructions outside the interface.
- **NFR-02 — Responsiveness:** The storefront shall remain usable from a 320-pixel-wide viewport through desktop widths.
- **NFR-03 — Accessibility:** Interactive elements shall be keyboard operable, form inputs shall have labels, dialogs shall expose appropriate roles, and information shall not depend solely on colour.
- **NFR-04 — Feedback:** Loading, empty, failure, validation, and successful-order states shall be visible to the shopper.
- **NFR-05 — Integrity:** Successful orders shall persist stock changes; rejected orders shall not change stored stock.
- **NFR-06 — Validation:** The API shall validate request types, string lengths, numeric bounds, and allowed enumerated values before processing.
- **NFR-07 — Portability:** The application shall run locally on current Python and Node.js versions using the documented commands.
- **NFR-08 — Testability:** Backend creation shall support an alternate catalog path so automated tests can use isolated data.
- **NFR-09 — Inspectability:** API operations shall be discoverable through generated OpenAPI documentation.
- **NFR-10 — Privacy:** Card input shall be used only for local demonstration validation and shall not be persisted.
- **NFR-11 — Maintainable contract:** Behaviour documented here shall remain stable during analysis and refactoring exercises.
- **NFR-12 — Performance:** With the supplied catalog, product-list and product-detail responses should complete within one second on a typical development machine.

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

