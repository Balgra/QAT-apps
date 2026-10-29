# Argentaria requirements

## Product description

Argentaria is a local desktop banking terminal for demonstration accounts. It provides card authentication and common cash-account interactions through a Tkinter interface. Account state and transaction history are stored in a local JSON-backed repository. It does not connect to a real bank, card network, or currency service.

## Functional requirements

- **FR-01 — Insert card:** The customer shall be able to start a session with a known card number and four-digit PIN.
- **FR-02 — Reject invalid access:** The system shall reject unknown cards, malformed credentials, incorrect PINs, and cards whose status is not active.
- **FR-03 — Eject card:** The customer shall be able to end the active session and return to card entry.
- **FR-04 — View balance:** An authenticated customer shall be able to see the available account balance in euros.
- **FR-05 — Convert balance:** The customer shall be able to view the euro balance in US dollars at `1 EUR = 1.1 USD` and Swedish kronor at `1 EUR = 9.5 SEK`.
- **FR-06 — Deposit euros:** The customer shall be able to deposit a positive euro amount with at most two decimal places and an optional note.
- **FR-07 — Deposit limit:** A single deposit shall not exceed EUR 5,000.
- **FR-08 — Withdraw euros:** The customer shall be able to withdraw a positive euro amount with at most two decimal places and an optional note when the account has sufficient available funds.
- **FR-09 — Withdrawal limit:** A single cash withdrawal shall not exceed EUR 1,000.
- **FR-10 — Apply account rules:** A current account may use its configured overdraft; a savings account may not withdraw beyond its balance.
- **FR-11 — Persist transactions:** Successful deposits and withdrawals shall update the stored balance and add a transaction with a unique reference, type, amount, resulting balance, time, and note.
- **FR-12 — Reject invalid transaction:** A rejected deposit or withdrawal shall not change the stored balance or transaction list.
- **FR-13 — View account details:** The customer shall be able to view holder contact details, address, account number, IBAN, account type, masked card number, and account-specific feature.
- **FR-14 — View recent activity:** The customer shall be able to see recent deposits and withdrawals.
- **FR-15 — View current and converted details:** The account-details view shall show the balance in EUR, USD, and SEK at the fixed training rates.
- **FR-16 — Transfer:** The customer shall be able to transfer up to EUR 5,000 to another known demonstration account; invalid destinations, self-transfers, and insufficient funds including fees shall be rejected.
- **FR-17 — Fees:** Before confirmation, the system shall present the operation amount and account-specific fee under the documented Current/Savings/Premium policy; a completed fee shall be recorded separately.
- **FR-18 — Daily limit:** Completed cash withdrawals shall not exceed EUR 1,000 per Europe/Stockholm calendar day across card sign-ins within the same application run, in addition to the single-operation limit.
- **FR-19 — Search history:** The customer shall be able to filter full history by inclusive dates, transaction type, and description/reference, with stable chronological sorting.
- **FR-20 — Statements:** The customer shall be able to export the selected history in text or CSV using English or Swedish import conventions, preserving dates, descriptions, signed EUR amounts, and historical balances.
- **FR-21 — Schedule:** The customer shall be able to schedule a one-off transfer to another known account on today or a future date.
- **FR-22 — Process payments:** The customer shall explicitly trigger processing of due payments; execution shall use the current fee policy and persist executed/failed outcomes without automatically retrying them.
- **FR-23 — Premium account:** The system shall support Premium accounts with their configured overdraft, zero operation fees, and corresponding statement representation.
- **FR-24 — PIN change:** An authenticated customer shall be able to replace a four-digit PIN after supplying the current PIN; the current and other old-credential sessions shall become unusable.
- **FR-25 — Block card:** An authenticated customer shall be able to block the current card and end its session; subsequent sign-in attempts shall be rejected.
- **FR-26 — Fresh startup:** Each application launch shall begin with the supplied accounts, balances, cards, PINs, and histories. Normal operations shall change only the current run's copy of the data.

## Non-functional requirements

- **NFR-01 — Usability:** The main banking actions shall be reachable from a persistent, clearly labelled navigation area after authentication.
- **NFR-02 — Feedback:** Authentication and transaction validation errors shall explain what the customer needs to correct.
- **NFR-03 — Confirmation:** A successful deposit or withdrawal shall show its transaction reference and resulting balance.
- **NFR-04 — Privacy:** The interface shall mask the displayed card number outside the card-entry field.
- **NFR-05 — Session isolation:** Banking functions shall reject calls made without an active authenticated session.
- **NFR-06 — Persistence:** Successful transaction state shall remain available after ending a card session and signing in again within the same application run.
- **NFR-07 — Portability:** The system shall run using Python's standard Tkinter distribution and shall require no network access.
- **NFR-08 — Testability:** Repository construction shall accept an alternate account-file path for isolated automated tests.
- **NFR-09 — Numerical consistency:** Stored balances and presented transaction amounts shall use two decimal places.
- **NFR-10 — Reproducibility:** Normal use shall leave the supplied account data unchanged, so each new application run begins from the same starting state.
- **NFR-11 — Maintainable contract:** Behaviour documented here shall remain stable during analysis and refactoring exercises.
- **NFR-12 — Responsiveness:** A user action against the supplied local data should complete within one second on a typical development machine.
- **NFR-13 — Transfer integrity:** In one application process, both account updates, linked history, and any fee shall commit atomically; a failed commit shall preserve storage and session balances.
- **NFR-14 — Compatibility:** English/Swedish CSV imported with the documented Excel/LibreOffice conventions shall preserve 100% of fixture rows and numeric totals. This is the acceptance target assessed in the README scenario.
- **NFR-15 — Amount validation:** Operations shall reject non-finite values, booleans, non-positive amounts, and excess decimal places without changing stored state.
- **NFR-16 — Deterministic time:** Daily-limit and scheduled-payment tests shall support an injected clock and isolated account data.

## Additional student implementation use cases

### UC-06 — Transfer or schedule money

**Actor:** Authenticated customer. **Precondition:** Active card and another known account.

1. The customer enters destination, amount, and optional note.
2. The system presents the fee and asks for confirmation.
3. The customer confirms an immediate transfer or supplies a due date.
4. For a scheduled payment, the customer later selects Process due payments.

**Alternatives:** Invalid destination, limit, or funds cause a rejection or persisted failed schedule. **Postcondition:** Immediate/executed transfers update both accounts once; due/failed/executed states remain inspectable within the current application run.

### UC-07 — Filter and exchange a statement

**Actor:** Authenticated customer. **Precondition:** An account with transaction history.

1. The customer selects dates, transaction type, or search text.
2. The system shows matching transactions.
3. The customer exports text, English CSV, or Swedish CSV and opens it with the documented spreadsheet settings.

**Postcondition:** Exported records and totals can be compared with the selected account history and compatibility target.

### UC-08 — Manage card access

**Actor:** Authenticated customer. **Precondition:** Active card session.

1. The customer supplies the current/new PIN or confirms card blocking.
2. The system saves the change and ends the session.
3. When the application is closed and launched again, the supplied demonstration credentials are available automatically.

**Alternatives:** Incorrect current PIN or invalid new PIN is rejected. **Postcondition:** Old credentials/blocked cards cannot access banking operations during that application run; the next launch starts with the documented demonstration credentials.

## Student implementation use cases

### UC-01 — Access an account

**Actor:** Bank customer  
**Goal:** Begin an authenticated terminal session.  
**Precondition:** A demonstration card account exists.

**Main flow:**

1. The customer enters a card number and PIN.
2. The authentication service locates the card and verifies its state and PIN.
3. The system creates an active card session.
4. The dashboard displays the customer's first name, masked card, and euro balance.

**Alternatives:** Unknown, inactive, malformed, or incorrectly authenticated cards are rejected with an explanatory message.

### UC-02 — Add money

**Actor:** Authenticated customer  
**Goal:** Increase the account balance.  
**Precondition:** The card session is active.

**Main flow:**

1. The customer opens **Add money**.
2. The customer enters a valid euro amount and optional note.
3. The system validates the amount, increases the balance, stores a deposit transaction, and persists the account.
4. The system confirms the transaction reference and new balance.

### UC-03 — Withdraw money

**Actor:** Authenticated customer  
**Goal:** Remove available money from the account.  
**Precondition:** The card session is active and the account has sufficient available funds.

**Main flow:**

1. The customer opens **Withdraw**.
2. The customer enters a valid euro amount and optional note.
3. The system applies transaction and account-type limits.
4. The system decreases the balance, stores a withdrawal transaction, persists the account, and confirms the result.

**Alternative:** Invalid, excessive, or unavailable amounts are rejected without changing account state.

### UC-04 — Inspect account and converted value

**Actor:** Authenticated customer  
**Goal:** Understand the account and the approximate value of its balance.  
**Precondition:** The card session is active.

**Main flow:**

1. The customer selects a dashboard display currency or opens **Account details**.
2. The system retrieves the account and customer information.
3. The currency service converts the euro balance using the fixed training rates.
4. The interface presents identity, banking references, account feature, and balances.

### UC-05 — End the session

**Actor:** Authenticated customer  
**Goal:** Leave the terminal safely.

**Main flow:**

1. The customer selects **Eject card**.
2. The system closes the active session and clears the selected display currency.
3. The card-entry screen is shown for the next customer.

