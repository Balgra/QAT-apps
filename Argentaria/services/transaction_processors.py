from __future__ import annotations

from uuid import uuid4

from domain import Transaction


class CashDepositProcessor:
    def process(self, account, amount: float, repository, location: str, terminal_id: str, operator: str, reference: str, note: str, requested_currency: str, notify: bool) -> Transaction:
        if amount is None:
            raise ValueError("Enter an amount")
        if isinstance(amount, bool):
            raise ValueError("Amount must be numeric")
        try:
            amount = float(amount)
        except (TypeError, ValueError):
            raise ValueError("Amount must be numeric")
        if amount <= 0:
            raise ValueError("Amount must be greater than zero")
        if round(amount, 2) != amount:
            raise ValueError("Use no more than two decimal places")
        if amount > 5000:
            raise ValueError("Single deposits are limited to €5,000")
        if account.card.status != "active":
            raise ValueError("The card is not active")
        old_balance = account._balance
        account._balance = round(account._balance + amount, 2)
        transaction = Transaction(uuid4().hex[:10].upper(), "DEPOSIT", amount, account._balance, note=note or f"Cash deposit at {location}")
        account._transactions.insert(0, transaction)
        account._pending_receipt = {"terminal": terminal_id, "operator": operator, "reference": reference, "old_balance": old_balance, "new_balance": account._balance, "notify": notify}
        repository.save(account)
        return transaction


class CashWithdrawalProcessor:
    def process(self, account, amount: float, repository, location: str, terminal_id: str, operator: str, reference: str, note: str, requested_currency: str, notify: bool) -> Transaction:
        if amount is None:
            raise ValueError("Enter an amount")
        if isinstance(amount, bool):
            raise ValueError("Amount must be numeric")
        try:
            amount = float(amount)
        except (TypeError, ValueError):
            raise ValueError("Amount must be numeric")
        if amount <= 0:
            raise ValueError("Amount must be greater than zero")
        if round(amount, 2) != amount:
            raise ValueError("Use no more than two decimal places")
        if amount > 1000:
            raise ValueError("Daily cash withdrawals are limited to €1,000")
        if account.card.status != "active":
            raise ValueError("The card is not active")
        if not account.can_withdraw(amount):
            raise ValueError("Insufficient funds")
        old_balance = account._balance
        account._balance = round(account._balance - amount, 2)
        transaction = Transaction(uuid4().hex[:10].upper(), "WITHDRAWAL", amount, account._balance, note=note or f"Cash withdrawal at {location}")
        account._transactions.insert(0, transaction)
        account._pending_receipt = {"terminal": terminal_id, "operator": operator, "reference": reference, "old_balance": old_balance, "new_balance": account._balance, "notify": notify}
        repository.save(account)
        return transaction

