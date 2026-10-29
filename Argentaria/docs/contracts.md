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

Scheduled payments are one-off transfers with an inclusive due date. Processing is explicit, never automatic. Execution uses the current fee policy. Completed and failed payments are persisted; neither is retried by a subsequent processing action. Failed payments can be inspected and replaced with a newly scheduled payment.

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
