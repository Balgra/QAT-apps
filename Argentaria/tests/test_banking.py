import json
from pathlib import Path

import pytest

from repository import AccountRepository
from services import BankingService, CardSessionGateway, CurrencyService
from services.authentication import CardAuthenticator


def setup_bank(tmp_path: Path):
    source = Path(__file__).parents[1] / "data" / "accounts.json"
    target = tmp_path / "accounts.json"
    target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    repository = AccountRepository(target)
    gateway = CardSessionGateway(CardAuthenticator(repository))
    service = BankingService(repository, CurrencyService())
    return gateway, service


def test_insert_card_and_view_balance(tmp_path):
    gateway, service = setup_bank(tmp_path)
    session = gateway.insert("4556123412341234", "1234")
    assert service.get_balance(session)["amount"] == 2450.75


def test_rejects_wrong_pin(tmp_path):
    gateway, _ = setup_bank(tmp_path)
    with pytest.raises(ValueError, match="Incorrect PIN"):
        gateway.insert("4556123412341234", "9999")


def test_deposit_and_withdraw_persist(tmp_path):
    gateway, service = setup_bank(tmp_path)
    session = gateway.insert("4556123412341234", "1234")
    assert service.deposit(session, 100)["balance"] == 2550.75
    assert service.withdraw(session, 50)["balance"] == 2500.75
    fresh_session = gateway.insert("4556123412341234", "1234")
    assert service.get_balance(fresh_session)["amount"] == 2500.75


def test_currency_rates(tmp_path):
    gateway, service = setup_bank(tmp_path)
    session = gateway.insert("4556123412341234", "1234")
    assert service.get_balance(session, "USD")["amount"] == round(2450.75 * 1.1, 2)
    assert service.get_balance(session, "SEK")["amount"] == round(2450.75 * 9.5, 2)


def test_account_details_include_identity_and_conversions(tmp_path):
    gateway, service = setup_bank(tmp_path)
    details = service.account_details(gateway.insert("4556123412341234", "1234"))
    assert details["holder"] == "Alex Lindberg"
    assert details["balance_usd"] == round(details["balance_eur"] * 1.1, 2)
    assert details["balance_sek"] == round(details["balance_eur"] * 9.5, 2)

