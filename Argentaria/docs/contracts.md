# Argentaria business and statement contracts

## Transactions and fees

All account operations use EUR and fixed two-decimal amounts. Non-finite values, booleans, non-positive amounts, and more than two decimal places are rejected. A deposit is capped at EUR 5,000; a transfer at EUR 5,000; each withdrawal and the cumulative daily cash withdrawal total are capped at EUR 1,000.

The daily boundary is Europe/Stockholm local midnight, including daylight saving time. Legacy timestamps without an offset are interpreted in that timezone. Completed withdrawals count across card sign-ins within the same application run; fees do not count toward withdrawn cash.

| Account | Withdrawal fee | Transfer fee | Overdraft |
| --- | --- | --- | --- |
| Current | <= 200: 0; > 200: 1 | <= 100: 0; > 100: 0.50 | Configured amount; primary demo EUR 300 |
| Savings | 1 | 2 | None |
| Premium | 0 | 0 | Configured amount; demo EUR 1,000 |

All deposits are free. Fees are presented before confirmation and stored as separate `FEE` transactions. Available funds must cover amount plus fee. Transfers persist linked `TRANSFER_OUT` and `TRANSFER_IN` records sharing a reference; the sender pays the fee. Debit equals recipient credit plus fee. Updates are committed together using one file replacement. Use one application process per state file.

Scheduled payments are one-off transfers with an inclusive due date. Processing is explicit, never automatic. **Process selected payments** immediately processes the selected pending payments, even if their due dates are in the future. **Process all due payments** processes only pending payments due today or earlier in Europe/Stockholm. The original due date remains recorded; `processed_at` records the actual execution/attempt time. The stored `due` state means pending and is displayed as **pending** in the table.

`preview_scheduled_payments(session, payment_ids)` returns the selected payment details, current per-payment fees, aggregate amounts/fees/debits, and the current balance. Omitting the IDs previews date-eligible pending payments. The UI confirms this quote, explicitly warning that future-dated selections will be paid immediately, and passes its payment details to `process_scheduled_payments` or `process_due_payments`. The processing step checks the quote again under the repository lock; a change in payment details or fees requires a new confirmation.

Successful execution retains `transaction_id`, `fee`, `total_debited`, the resulting balance, and `processed_at` on the payment. Sender/recipient transfers share a reference and any fee has a separate linked history entry. Failed payments retain the error and processing time with zero fee/debit. Each payment uses fresh account state, so funds are checked after earlier successful payments in the same batch. One payment can fail while another succeeds; a validation failure never commits a partially completed transfer. A storage error rolls back the entire batch, including payment statuses and session balances.

Only pending payments in the authenticated account may be selected. Empty/duplicate/unknown references and executed/failed selections are rejected before transfers occur. Completed and failed payments are retained but cannot be processed again, including under concurrent attempts. Failed payments can be inspected and replaced with a newly scheduled payment. Previews and processing inputs/outcomes are included in the activity log.

Changing a four-digit PIN requires the current PIN and ends the card session. Blocking also ends the card session. Other sessions become invalid on their next operation after PIN change/blocking. Changes remain effective for the current application run. Each launch of `app.py` copies the supplied `data/accounts.json` into a temporary session directory, so closing and launching the application restores the same demonstration accounts and credentials automatically. The supplied file is unchanged.

## Statement export

The customer chooses full or filtered history with inclusive start/end dates, transaction type, and description/reference search. Sorting is timestamp order with stable ordering for ties. Text statements show the account details and the selected rows. CSV statements contain six columns:

`Date`, `Reference`, `Type`, `Description`, `Amount EUR`, `Balance EUR`.

Withdrawals, outbound transfers, and fees have negative signed CSV amounts. Deposits and incoming transfers are positive. Dates use the same Europe/Stockholm calendar day as history filtering. Balances are historical balances after each recorded event, not recomputed from a filtered subset. The UI writes CSV with UTF-8 BOM and CRLF line endings; quoted punctuation/newlines in descriptions must round-trip intact.

## Compatibility acceptance conventions

| Convention | English | Swedish |
| --- | --- | --- |
| Encoding | UTF-8 (BOM allowed) | UTF-8 (BOM allowed) |
| Separator | Comma | Semicolon |
| Decimal separator | Point | Comma |
| Dates | ISO `YYYY-MM-DD` | ISO `YYYY-MM-DD` |
| Amount interpretation | Signed numeric EUR | Signed numeric EUR |

These are explicit import settings to use in Excel/LibreOffice's text-import dialog. Record application version and import settings in any manual result. Reference-parser tests do not establish that a real spreadsheet was exercised.

The current English export matches the conventions. The Swedish path currently emits decimal points and slash-separated dates; its two acceptance probes are strict expected failures. Run `python -B -m pytest -p no:cacheprovider tests/test_compatibility.py --runxfail` to observe those failures. Text export and the ordinary banking paths remain usable independently.

## Public service methods

`BankingService` supplies `quote_fee`, `deposit`, `withdraw`, `transfer`, `history`, `export_statement`, `schedule_payment`, `scheduled_payments`, `process_due_payments`, `change_pin`, and `block_card`. Each requires an active session. `CurrentStatement`, `SavingsStatement`, and `PremiumStatement` render the corresponding account types; rate conversion remains EUR 1 = USD 1.1 = SEK 9.5.
