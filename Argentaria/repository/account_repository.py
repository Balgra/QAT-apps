from __future__ import annotations

import json
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from threading import RLock

from domain import Address, BankCard, CurrentAccount, Customer, CustomerProfile, SavingsAccount, Transaction
from domain import PremiumAccount


class AccountRepository:
    def __init__(self, data_file: Path):
        self.data_file = data_file
        self.lock = RLock()

    def _to_account(self, row: dict):
        address = Address(row["customer"]["street"], row["customer"]["city"], row["customer"]["postal_code"], row["customer"]["country"])
        profile = CustomerProfile(row["customer"]["email"], row["customer"]["phone"], address)
        customer = Customer(row["customer"]["customer_id"], row["customer"]["full_name"], profile)
        card = BankCard(row["card"]["number"], row["card"]["pin"], row["card"]["expiry"], row["card"]["status"], customer)
        transactions = [Transaction(item["transaction_id"], item["kind"], item["amount"], item["balance_after"], item["timestamp"], item.get("note", "")) for item in row.get("transactions", [])]
        if row["account_type"] == "Savings":
            account = SavingsAccount(row["account_number"], row["iban"], row["balance"], row["currency"], card, transactions, row.get("interest_rate", 0.012))
        elif row["account_type"] == "Premium":
            account = PremiumAccount(row["account_number"], row["iban"], row["balance"], row["currency"], card, transactions, row.get("overdraft", 1000))
        else:
            account = CurrentAccount(row["account_number"], row["iban"], row["balance"], row["currency"], card, transactions, row.get("overdraft", 200))
        account._scheduled_payments = row.get("scheduled_payments", [])
        return account

    def _to_row(self, account) -> dict:
        customer = account.card.customer
        return {
            "account_number": account.account_number,
            "iban": account.iban,
            "account_type": account.account_type,
            "balance": round(account._balance, 2),
            "currency": account.currency,
            "overdraft": getattr(account, "overdraft", 0),
            "interest_rate": getattr(account, "interest_rate", 0),
            "card": {"number": account.card.number, "pin": account.card._pin, "expiry": account.card.expiry, "status": account.card.status},
            "customer": {
                "customer_id": customer.customer_id,
                "full_name": customer.full_name,
                "email": customer.profile.email,
                "phone": customer.profile.phone,
                "street": customer.profile.address.street,
                "city": customer.profile.address.city,
                "postal_code": customer.profile.address.postal_code,
                "country": customer.profile.address.country,
            },
            "transactions": [item.as_dict() for item in account._transactions],
            "scheduled_payments": account._scheduled_payments,
        }

    def get_all(self) -> list:
        with self.data_file.open("r", encoding="utf-8") as handle:
            rows = json.load(handle)
        return [self._to_account(row) for row in rows]

    def find_by_card(self, card_number: str):
        with self.data_file.open("r", encoding="utf-8") as handle:
            rows = json.load(handle)
        accounts = [self._to_account(row) for row in rows]
        found = None
        for account in accounts:
            if account.card.number.replace(" ", "") == card_number.replace(" ", ""):
                found = account
        return found

    def find_by_account_number(self, account_number: str):
        with self.data_file.open("r", encoding="utf-8") as handle:
            rows = json.load(handle)
        accounts = [self._to_account(row) for row in rows]
        found = None
        for account in accounts:
            if account.account_number.replace(" ", "") == account_number.replace(" ", ""):
                found = account
        return found

    def save(self, changed_account) -> None:
        with self.transaction() as accounts:
            for index, account in enumerate(accounts):
                if account.account_number == changed_account.account_number:
                    accounts[index] = changed_account

    def update_card_status(self, card_number: str, status: str) -> None:
        with self.transaction() as accounts:
            for account in accounts:
                if account.card.number.replace(" ", "") == card_number.replace(" ", ""):
                    account.card.status = status

    def _commit(self, accounts):
        descriptor, name = tempfile.mkstemp(prefix="argentaria-", suffix=".tmp", dir=self.data_file.parent)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as output:
                json.dump([self._to_row(a) for a in accounts], output, indent=2, ensure_ascii=False, allow_nan=False)
                output.flush()
                os.fsync(output.fileno())
            os.replace(name, self.data_file)
        finally:
            if os.path.exists(name):
                os.unlink(name)

    @contextmanager
    def transaction(self):
        with self.lock:
            accounts = self.get_all()
            yield accounts
            self._commit(accounts)

