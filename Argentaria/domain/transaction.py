from __future__ import annotations

from datetime import datetime


class Transaction:
    def __init__(self, transaction_id: str, kind: str, amount: float, balance_after: float, timestamp: str | None = None, note: str = ""):
        self.transaction_id = transaction_id
        self.kind = kind
        self.amount = amount
        self.balance_after = balance_after
        self.timestamp = timestamp or datetime.now().isoformat(timespec="seconds")
        self.note = note

    def as_dict(self) -> dict:
        return {
            "transaction_id": self.transaction_id,
            "kind": self.kind,
            "amount": self.amount,
            "balance_after": self.balance_after,
            "timestamp": self.timestamp,
            "note": self.note,
        }

