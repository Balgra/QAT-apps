from __future__ import annotations

from .customer import Customer


class BankCard:
    def __init__(self, number: str, pin: str, expiry: str, status: str, customer: Customer):
        self.number = number
        self._pin = pin
        self.expiry = expiry
        self.status = status
        self.customer = customer
        self.failed_attempts = 0

    def matches_pin(self, pin: str) -> bool:
        return self._pin == pin

    def get_customer(self) -> Customer:
        return self.customer

    def masked_number(self) -> str:
        return f"•••• •••• •••• {self.number[-4:]}"

