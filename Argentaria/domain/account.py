from __future__ import annotations

from .card import BankCard
from .transaction import Transaction


class Account:
    def __init__(self, account_number: str, iban: str, account_type: str, balance: float, currency: str, card: BankCard, transactions: list[Transaction] | None = None):
        self.account_number = account_number
        self.iban = iban
        self.account_type = account_type
        self._balance = float(balance)
        self.currency = currency
        self.card = card
        self._transactions = transactions or []
        self._pending_receipt = None
        self._last_audit_message = None
        self._scheduled_payments = []

    def get_balance(self) -> float:
        return round(self._balance, 2)

    def get_card(self) -> BankCard:
        return self.card

    def get_transactions(self) -> list[Transaction]:
        return self._transactions

    def can_withdraw(self, amount: float) -> bool:
        return 0 < amount <= self._balance

    def calculate_monthly_interest(self) -> float:
        return 0.0

    def overdraft_limit(self) -> float:
        return 0.0


class SavingsAccount(Account):
    def __init__(self, account_number: str, iban: str, balance: float, currency: str, card: BankCard, transactions: list[Transaction] | None = None, interest_rate: float = 0.012):
        super().__init__(account_number, iban, "Savings", balance, currency, card, transactions)
        self.interest_rate = interest_rate

    def calculate_monthly_interest(self) -> float:
        return round(self._balance * self.interest_rate / 12, 2)

    def overdraft_limit(self) -> float:
        raise RuntimeError("Savings accounts do not offer overdrafts")


class CurrentAccount(Account):
    def __init__(self, account_number: str, iban: str, balance: float, currency: str, card: BankCard, transactions: list[Transaction] | None = None, overdraft: float = 200.0):
        super().__init__(account_number, iban, "Current", balance, currency, card, transactions)
        self.overdraft = overdraft

    def can_withdraw(self, amount: float) -> bool:
        return 0 < amount <= self._balance + self.overdraft

    def calculate_monthly_interest(self) -> float:
        raise RuntimeError("Current accounts do not accrue savings interest")

    def overdraft_limit(self) -> float:
        return self.overdraft


class PremiumAccount(CurrentAccount):
    def __init__(self, account_number, iban, balance, currency, card, transactions=None, overdraft=1000):
        super().__init__(account_number, iban, balance, currency, card, transactions, overdraft)
        self.account_type = "Premium"

    def overdraft_limit(self):
        return self.overdraft

