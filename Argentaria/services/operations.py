from __future__ import annotations

from decimal import Decimal, InvalidOperation
from uuid import uuid4

from domain import Transaction


def amount_value(value):
    if isinstance(value, bool):
        raise ValueError("Amount must be numeric")
    try:
        number = Decimal(str(value))
        if not number.is_finite() or number <= 0 or number > Decimal("1000000"):
            raise ValueError("Amount must be positive and no greater than EUR 1,000,000")
        if number != number.quantize(Decimal("0.01")):
            raise ValueError("Use no more than two decimal places")
        return float(number)
    except (InvalidOperation, TypeError):
        raise ValueError("Amount must be numeric")


class AccountPolicy:
    def fee(self, operation, amount):
        raise NotImplementedError


class CurrentPolicy(AccountPolicy):
    def fee(self, operation, amount):
        if operation == "withdraw":
            return 0 if amount <= 200 else 1
        if operation == "transfer":
            return 0 if amount <= 100 else 0.5
        return 0


class SavingsPolicy(AccountPolicy):
    def fee(self, operation, amount):
        if operation == "withdraw":
            return 1
        if operation == "transfer":
            return 2
        return 0


class PremiumPolicy(AccountPolicy):
    def fee(self, operation, amount):
        return 0


class FeeProcessor:
    def quote(self, account, operation, amount):
        if account.account_type == "Savings":
            policy = SavingsPolicy()
        elif account.account_type == "Premium":
            policy = PremiumPolicy()
        else:
            policy = CurrentPolicy()
        return policy.fee(operation, amount)

    def apply(self, account, fee, timestamp, reference):
        if fee:
            account._balance = round(account._balance - fee, 2)
            account._transactions.insert(0, Transaction(uuid4().hex[:10].upper(), "FEE", fee,
                                                        account._balance, timestamp, f"Fee for {reference}"))


class TransferProcessor:
    def process(self, account, destination, amount, repository, location, terminal_id, operator, reference, note, requested_currency, notify, timestamp):
        if amount is None:
            raise ValueError("Enter an amount")
        if isinstance(amount, bool):
            raise ValueError("Amount must be numeric")
        try:
            number = Decimal(str(amount))
            if not number.is_finite() or number != number.quantize(Decimal("0.01")):
                raise ValueError("Use a finite amount with at most two decimal places")
            amount = float(number)
        except (TypeError, ValueError, InvalidOperation):
            raise ValueError("Amount must be numeric")
        if amount <= 0:
            raise ValueError("Amount must be greater than zero")
        if round(amount, 2) != amount:
            raise ValueError("Use no more than two decimal places")
        if amount > 5000:
            raise ValueError("Single transfers are limited to EUR 5,000")
        if account.card.status != "active":
            raise ValueError("The card is not active")
        if destination.account_number == account.account_number:
            raise ValueError("Choose a different destination account")
        if not account.can_withdraw(amount):
            raise ValueError("Insufficient funds")
        old_balance = account._balance
        account._balance = round(account._balance - amount, 2)
        destination._balance = round(destination._balance + amount, 2)
        key = uuid4().hex[:10].upper()
        transaction = Transaction(key, "TRANSFER_OUT", amount, account._balance, timestamp, note or f"Transfer to {destination.account_number}")
        received = Transaction(key, "TRANSFER_IN", amount, destination._balance, timestamp, note or f"Transfer from {account.account_number}")
        account._transactions.insert(0, transaction)
        destination._transactions.insert(0, received)
        account._pending_receipt = {"terminal": terminal_id, "operator": operator, "reference": reference,
                                    "old_balance": old_balance, "new_balance": account._balance, "notify": notify}
        return transaction
