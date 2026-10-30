# Argentaria activity log

The desktop creates one activity recorder when it opens. It lasts across card sign-ins and ejections during that application run. The **Download activity log** button below **Eject card**, and the same button on the card-entry screen, save a UTF-8 JSON snapshot chosen through the normal file dialog. No additional dependency is required.

## Recorded behavior

- Navigation between the card-entry screen and banking screens.
- Card insertion, including failed sign-ins, and ejection.
- Public banking operations: balances/conversions, account details, deposits, withdrawals, fee quotes, transfers, history, statements, scheduling/processing, PIN changes, and card blocking.
- Scheduled-payment previews and selected/due processing, including selected references, confirmed details/fees, actual debits, results, and rejected attempts. Future-dated selections retain their original due date alongside the actual processing time.
- Cancelled cash/transfer confirmations and rejected cash-form input.

Service calls used internally to prepare a screen or export also appear. For example, statement generation can produce account-details, history, and export-statement entries. This makes the performed backend work visible; event counts are not necessarily the number of button clicks. Each operation retains its original result or exception.

## Export fields

| Field | Meaning |
| --- | --- |
| `schema_version` | Export format version, currently `1` |
| `application`, `session_id` | Application name and identifier of the current application run |
| `started_at`, `exported_at` | UTC timestamps with timezone offsets |
| `events` | Completed observations in recording/completion order |
| Event `sequence`, `timestamp` | Sequence number and UTC recording time |
| `action` | Such as `navigation`, `card.insert`, `card.eject`, or `banking.deposit` |
| `request` | Named input parameters, including defaults, with credentials redacted |
| `response` | Returned result, or `null` for errors/actions without a return value |
| `error` | Exception type/message, or `null` on success |
| `duration_ms` | Measured service-call duration; immediate UI observations use zero |

Example service event (timestamps, sequence, and duration omitted):

```json
{
  "action": "banking.deposit",
  "request": {
    "session": {"type": "CardSession"},
    "amount": 20,
    "note": "Göteborg café"
  },
  "response": {
    "transaction_id": "EXAMPLE",
    "amount": 20,
    "fee": 0,
    "balance": 2470.75,
    "kind": "DEPOSIT"
  },
  "error": null
}
```

PIN fields and full card-number inputs are redacted recursively. Unknown session/domain objects are represented by their type without traversing private attributes; dictionaries/lists are copied so later account or payment changes cannot rewrite earlier observations. Invalid non-finite numbers are represented as strings, keeping the export valid JSON. Other demonstration customer data, transaction notes, and exported statement contents remain visible.

Save the log before closing the app; a new launch starts an empty log. Downloading neither clears the log nor changes balances/cards. The export itself is not recorded recursively. Cancelling the file dialog changes nothing. Exports replace the destination only after the complete JSON has been written; a failed save preserves any previous download, cleans up its temporary file, and shows an error so it can be retried.

Implementation: `services/activity_log.py` provides the recorder and the public-service decorator. The desktop injects the recorder into `CardSessionGateway` and `BankingService`. Existing standalone service construction works without a recorder. Tests are in `tests/test_activity_log.py` and `tests/test_ui.py`.
