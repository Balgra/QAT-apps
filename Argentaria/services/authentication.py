from __future__ import annotations

from datetime import datetime
from datetime import timezone

from repository import AccountRepository


class CardSession:
    def __init__(self, account, started_at: datetime):
        self.account = account
        self.started_at = started_at
        self.active = True

    def get_account(self):
        return self.account

    def close(self) -> None:
        self.active = False


class CardAuthenticator:
    def __init__(self, repository: AccountRepository, clock=None):
        self.repository = repository
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def authenticate(self, card_number: str, pin: str) -> CardSession:
        if not card_number:
            raise ValueError("Insert a card number")
        if not pin:
            raise ValueError("Enter a PIN")
        if not card_number.replace(" ", "").isdigit():
            raise ValueError("Card number must contain digits only")
        if not pin.isdigit() or len(pin) != 4:
            raise ValueError("PIN must contain four digits")
        account = self.repository.find_by_card(card_number)
        if account is None:
            raise ValueError("Card was not recognised")
        if account.card.status == "blocked":
            raise ValueError("This card is blocked")
        if account.card.status == "expired":
            raise ValueError("This card has expired")
        if account.card.status != "active":
            raise ValueError("This card is not active")
        month, year = account.card.expiry.split("/")
        now = self.clock()
        if (2000 + int(year), int(month)) < (now.year, now.month):
            raise ValueError("This card has expired")
        if not account.card.matches_pin(pin):
            account.card.failed_attempts += 1
            raise ValueError("Incorrect PIN")
        return CardSession(account, datetime.now())


class CardSessionGateway:
    def __init__(self, authenticator: CardAuthenticator):
        self.authenticator = authenticator

    def insert(self, card_number: str, pin: str) -> CardSession:
        return self.authenticator.authenticate(card_number, pin)

