from datetime import datetime, timezone

import pytest

from domain import Account, CurrentAccount, PremiumAccount, SavingsAccount
from services.authentication import CardAuthenticator
from services.currency_service import CurrencyService
from test_operations import bank


@pytest.mark.parametrize("card,pin", [
    ("", "1234"), ("4556123412341234", ""), ("not-a-card", "1234"),
    ("4556123412341234", "123"), ("4556123412341234", "12345"),
    ("4556123412341234", "abcd"), ("0000000000000000", "1234"),
])
def test_authentication_rejects_missing_malformed_or_unknown_credentials(bank, card, pin):
    _, _, repo, gateway, _ = bank
    before = repo.data_file.read_bytes()
    with pytest.raises(ValueError):
        gateway.insert(card, pin)
    assert repo.data_file.read_bytes() == before


@pytest.mark.parametrize("status", ["blocked", "expired", "suspended"])
def test_non_active_card_statuses_cannot_authenticate(bank, status):
    _, _, repo, gateway, _ = bank
    repo.update_card_status("4556 1234 1234 1234", status)
    with pytest.raises(ValueError):
        gateway.insert("4556123412341234", "1234")


@pytest.mark.parametrize("expiry,accepted", [("09/26", False), ("10/26", True), ("11/26", True), ("12/25", False)])
def test_authentication_expiry_month_boundaries(bank, expiry, accepted):
    _, _, repo, _, now = bank
    account = repo.find_by_card("4556123412341234")
    account.card.expiry = expiry
    repo.save(account)
    authenticator = CardAuthenticator(repo, lambda: now[0])
    if accepted:
        assert authenticator.authenticate("4556 1234 1234 1234", "1234").active
    else:
        with pytest.raises(ValueError, match="expired"):
            authenticator.authenticate("4556123412341234", "1234")


@pytest.mark.parametrize("amount,allowed", [(0, False), (.01, True), (99.99, True), (100, True), (100.01, False)])
@pytest.mark.parametrize("subtype", [Account, SavingsAccount])
def test_non_overdraft_account_balance_boundaries(bank, amount, allowed, subtype):
    card = bank[1].get_account().get_card()
    if subtype is Account:
        account = Account("fixture", "fixture-iban", "Basic", 100, "EUR", card)
    else:
        account = SavingsAccount("fixture", "fixture-iban", 100, "EUR", card)
    assert account.can_withdraw(amount) is allowed


@pytest.mark.parametrize("amount,allowed", [(0, False), (.01, True), (399.99, True), (400, True), (400.01, False)])
@pytest.mark.parametrize("subtype", [CurrentAccount, PremiumAccount])
def test_overdraft_account_balance_boundaries(bank, amount, allowed, subtype):
    account = subtype("fixture", "fixture-iban", 100, "EUR", bank[1].get_account().get_card(), overdraft=300)
    assert account.can_withdraw(amount) is allowed
    assert account.overdraft_limit() == 300


@pytest.mark.parametrize("balance,interest", [(0, 0), (100, .1), (1000, 1), (8120, 8.12)])
def test_savings_monthly_interest_examples(bank, balance, interest):
    account = SavingsAccount("fixture", "fixture-iban", balance, "EUR", bank[1].get_account().get_card(), interest_rate=.012)
    assert account.calculate_monthly_interest() == interest


@pytest.mark.parametrize("currency,amount,symbol", [("EUR", 100, "€"), ("USD", 110, "$"), ("SEK", 950, "kr")])
def test_supported_currency_conversion_and_labels(currency, amount, symbol):
    service = CurrencyService()
    assert service.convert(100, currency) == amount
    assert service.label_for(currency) == symbol


@pytest.mark.parametrize("amount,expected", [(0, 0), (.01, .01), (-10, -11)])
def test_currency_zero_small_and_overdraft_values(amount, expected):
    assert CurrencyService().convert(amount, "USD") == expected


def test_currency_rejects_unsupported_conversion_but_preserves_unknown_label():
    with pytest.raises(ValueError):
        CurrencyService().convert(1, "GBP")
    assert CurrencyService().label_for("GBP") == "GBP"


def test_profile_address_card_and_session_outputs(bank):
    _, session, _, _, _ = bank
    account = session.get_account()
    assert account.get_card().get_customer().full_name == "Fixture Customer"
    address = account.get_card().get_customer().get_profile().get_address().formatted()
    assert "Gothenburg" in address and "Sweden" in address
    masked = account.get_card().masked_number()
    assert masked.endswith("1234") and account.get_card().number not in masked
    assert account.get_card().matches_pin("1234")
    assert not account.get_card().matches_pin("9999")
    session.close()
    assert not session.active
