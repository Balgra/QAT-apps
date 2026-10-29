import json
from datetime import datetime, timedelta, timezone

import pytest

from services.operations import amount_value
from test_operations import bank


def configure(bank, account_type="Current", balance=10000, overdraft=300):
    service, session, repo, gateway, _ = bank
    rows = json.loads(repo.data_file.read_text(encoding="utf-8"))
    rows[0].update(account_type=account_type, balance=balance, overdraft=overdraft)
    repo.data_file.write_text(json.dumps(rows), encoding="utf-8")
    return gateway.insert("4556123412341234", "1234")


@pytest.mark.parametrize("operation,limit", [("deposit", 5000), ("withdraw", 1000), ("transfer", 5000)])
@pytest.mark.parametrize("position", ["below-zero", "zero", "minimum", "next", "below-max", "maximum", "above-max"])
def test_transaction_amount_boundaries(bank, operation, limit, position):
    service, _, repo, _, _ = bank
    session = configure(bank)
    amount = {"below-zero": -.01, "zero": 0, "minimum": .01, "next": .02,
              "below-max": limit - .01, "maximum": limit, "above-max": limit + .01}[position]
    before = repo.data_file.read_bytes()
    def execute():
        if operation == "transfer":
            return service.transfer(session, "1000 2200 7788", amount)
        return getattr(service, operation)(session, amount)
    if position in {"below-zero", "zero", "above-max"}:
        with pytest.raises(ValueError):
            execute()
        assert repo.data_file.read_bytes() == before
    else:
        fee = service.quote_fee(session, operation, amount)["fee"]
        result = execute()
        assert result["amount"] == amount
        expected = 10000 + amount if operation == "deposit" else 10000 - amount - fee
        assert result["balance"] == pytest.approx(expected)


@pytest.mark.parametrize("value,expected", [("0.01", .01), ("1000000.00", 1000000), ("1e2", 100), (1, 1)])
def test_amount_parser_valid_numeric_boundaries(value, expected):
    assert amount_value(value) == expected


@pytest.mark.parametrize("value", [None, "", "invalid", "0.001", "1000000.01", "-inf", "NaN", False])
def test_amount_parser_invalid_boundaries(value):
    with pytest.raises(ValueError):
        amount_value(value)


@pytest.mark.parametrize("operation,amount,expected", [
    ("withdraw", 199.99, 0), ("withdraw", 200, 0), ("withdraw", 200.01, 1),
    ("transfer", 99.99, 0), ("transfer", 100, 0), ("transfer", 100.01, .5),
])
def test_current_fee_thresholds(bank, operation, amount, expected):
    service, session, _, _, _ = bank
    assert service.quote_fee(session, operation, amount) == {"amount": amount, "fee": expected, "total": round(amount + expected, 2)}


@pytest.mark.parametrize("account_type,operation,fee", [
    ("Savings", "withdraw", 1), ("Savings", "transfer", 2), ("Savings", "deposit", 0),
    ("Premium", "withdraw", 0), ("Premium", "transfer", 0), ("Premium", "deposit", 0), ("Current", "deposit", 0),
])
def test_all_account_policy_operations(bank, account_type, operation, fee):
    session = configure(bank, account_type)
    assert bank[0].quote_fee(session, operation, 50)["fee"] == fee


@pytest.mark.parametrize("account_type,amount,limit,fee", [("Current", 250, 300, 1), ("Savings", 50, 0, 1), ("Premium", 250, 1000, 0)])
@pytest.mark.parametrize("offset", [-.01, 0, .01])
def test_available_funds_including_fee_boundary(bank, account_type, amount, limit, fee, offset):
    service, _, repo, _, _ = bank
    # Set balance so amount + fee is exactly at, one cent below, or one cent above availability.
    balance = round(amount + fee - limit + offset, 2)
    session = configure(bank, account_type, balance, limit)
    before = repo.data_file.read_bytes()
    if offset < 0:
        with pytest.raises(ValueError, match="Insufficient"):
            service.withdraw(session, amount)
        assert repo.data_file.read_bytes() == before
    else:
        assert service.withdraw(session, amount)["balance"] == pytest.approx(-limit + offset)


@pytest.mark.parametrize("previous,amount,accepted", [(999.98, .01, True), (999.99, .01, True), (1000, .01, False)])
def test_cumulative_daily_total_cent_boundaries(bank, previous, amount, accepted):
    service, _, repo, gateway, _ = bank
    session = configure(bank)
    service.withdraw(session, previous)
    session = gateway.insert("4556123412341234", "1234")
    if accepted:
        assert service.withdraw(session, amount)["amount"] == amount
    else:
        before = repo.data_file.read_bytes()
        with pytest.raises(ValueError, match="Daily"):
            service.withdraw(session, amount)
        assert repo.data_file.read_bytes() == before


@pytest.mark.parametrize("utc_before,utc_after", [
    (datetime(2026, 7, 1, 21, 59, 59, tzinfo=timezone.utc), datetime(2026, 7, 1, 22, 0, tzinfo=timezone.utc)),
    (datetime(2026, 12, 1, 22, 59, 59, tzinfo=timezone.utc), datetime(2026, 12, 1, 23, 0, tzinfo=timezone.utc)),
])
def test_daily_boundary_in_summer_and_winter(bank, utc_before, utc_after):
    service, _, _, _, now = bank
    session = configure(bank)
    now[0] = utc_before
    service.withdraw(session, 1000)
    with pytest.raises(ValueError):
        service.withdraw(session, .01)
    now[0] = utc_after
    assert service.withdraw(session, .01)["amount"] == .01


@pytest.mark.parametrize("change,accepted", [(-1, False), (0, True), (1, True)])
def test_schedule_date_boundaries(bank, change, accepted):
    service, session, repo, _, now = bank
    due = (now[0].date() + timedelta(days=change)).isoformat()
    before = repo.data_file.read_bytes()
    if accepted:
        payment = service.schedule_payment(session, "1000 2200 7788", 50, due)
        assert service.scheduled_payments(session)[0] == payment
        assert len(service.process_due_payments(session)) == (1 if change == 0 else 0)
    else:
        with pytest.raises(ValueError):
            service.schedule_payment(session, "1000 2200 7788", 50, due)
        assert repo.data_file.read_bytes() == before


@pytest.mark.parametrize("amount,accepted", [(4999.99, True), (5000, True), (5000.01, False)])
def test_schedule_amount_maximum(bank, amount, accepted):
    service, session, _, _, _ = bank
    if accepted:
        assert service.schedule_payment(session, "1000 2200 7788", amount, "2026-10-30")["amount"] == amount
    else:
        with pytest.raises(ValueError):
            service.schedule_payment(session, "1000 2200 7788", amount, "2026-10-30")


@pytest.mark.parametrize("destination", ["missing", "1000 2200 3344"])
def test_schedule_destination_rejected_without_writing(bank, destination):
    service, session, repo, _, _ = bank
    before = repo.data_file.read_bytes()
    with pytest.raises(ValueError):
        service.schedule_payment(session, destination, 50, "2026-10-30")
    assert repo.data_file.read_bytes() == before


@pytest.mark.parametrize("new_pin", ["", "123", "12345", "12ab", "１２３４"])
def test_pin_length_and_character_boundaries(bank, new_pin):
    service, session, repo, gateway, _ = bank
    before = repo.data_file.read_bytes()
    with pytest.raises(ValueError):
        service.change_pin(session, "1234", new_pin)
    assert repo.data_file.read_bytes() == before
    assert gateway.insert("4556123412341234", "1234").active


def test_wrong_current_pin_and_closed_session(bank):
    service, session, repo, _, _ = bank
    before = repo.data_file.read_bytes()
    with pytest.raises(ValueError, match="current PIN"):
        service.change_pin(session, "9999", "5678")
    assert repo.data_file.read_bytes() == before
    session.close()
    with pytest.raises(ValueError):
        service.deposit(session, 1)


@pytest.mark.parametrize("operation", ["balance", "details", "fee", "history", "export", "scheduled", "process", "block", "transfer", "deposit", "withdraw", "pin", "schedule"])
def test_public_service_operations_require_a_session(bank, operation):
    service = bank[0]
    calls = {
        "balance": lambda: service.get_balance(None), "details": lambda: service.account_details(None),
        "fee": lambda: service.quote_fee(None, "deposit", 1), "history": lambda: service.history(None),
        "export": lambda: service.export_statement(None), "scheduled": lambda: service.scheduled_payments(None),
        "process": lambda: service.process_due_payments(None), "block": lambda: service.block_card(None),
        "transfer": lambda: service.transfer(None, "1000 2200 7788", 1),
        "deposit": lambda: service.deposit(None, 1), "withdraw": lambda: service.withdraw(None, 1),
        "pin": lambda: service.change_pin(None, "1234", "5678"),
        "schedule": lambda: service.schedule_payment(None, "1000 2200 7788", 1, "2026-10-30"),
    }
    before = bank[2].data_file.read_bytes()
    with pytest.raises(ValueError):
        calls[operation]()
    assert bank[2].data_file.read_bytes() == before
