import csv
import io
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from repository import AccountRepository
from services import BankingService, CardSessionGateway, CurrencyService
from services.authentication import CardAuthenticator


@pytest.fixture
def bank(tmp_path):
    rows = json.loads((Path(__file__).parents[1] / "data/accounts.json").read_text(encoding="utf-8"))
    rows[0]["customer"]["full_name"] = "Fixture Customer"
    rows[0]["balance"] = 2450.75
    rows[0]["transactions"] = []
    rows[0]["scheduled_payments"] = []
    rows[0]["card"].update(pin="1234", status="active", expiry="12/35")
    rows[1]["balance"] = 8120
    rows[1]["transactions"] = []
    target = tmp_path / "accounts.json"
    target.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    now = [datetime(2026, 10, 29, 12, tzinfo=timezone.utc)]
    repo = AccountRepository(target)
    gateway = CardSessionGateway(CardAuthenticator(repo, lambda: now[0]))
    service = BankingService(repo, CurrencyService(), lambda: now[0])
    session = gateway.insert("4556123412341234", "1234")
    return service, session, repo, gateway, now


def test_transfer_reconciles_fee_and_survives_restart(bank):
    service, session, repo, gateway, _ = bank
    before = repo.find_by_account_number("1000 2200 7788").get_balance()
    result = service.transfer(session, "1000 2200 7788", 200, "Rent")
    assert result["fee"] == 0.5
    assert result["balance"] == 2250.25
    assert repo.find_by_account_number("1000 2200 7788").get_balance() == before + 200
    assert service.get_balance(gateway.insert("4556123412341234", "1234"))["amount"] == result["balance"]
    outgoing = next(t for t in session.account._transactions if t.kind == "TRANSFER_OUT")
    incoming = repo.find_by_account_number("1000 2200 7788")._transactions[0]
    assert outgoing.transaction_id == incoming.transaction_id


@pytest.mark.parametrize("amount", [0, -1, True, "nan", "inf", "1.001", "not money", "1e9999999"])
@pytest.mark.parametrize("operation", ["deposit", "withdraw", "transfer"])
def test_invalid_amounts_do_not_change_state(bank, amount, operation):
    service, session, repo, _, _ = bank
    before = repo.data_file.read_bytes()
    with pytest.raises(ValueError):
        if operation == "transfer":
            service.transfer(session, "1000 2200 7788", amount)
        else:
            getattr(service, operation)(session, amount)
    assert repo.data_file.read_bytes() == before
    assert session.account.get_balance() == 2450.75


@pytest.mark.parametrize("destination", ["unknown", "1000 2200 3344"])
def test_invalid_destination(bank, destination):
    service, session, repo, _, _ = bank
    before = repo.data_file.read_bytes()
    with pytest.raises(ValueError):
        service.transfer(session, destination, 50)
    assert repo.data_file.read_bytes() == before


def test_commit_failure_does_not_mutate_session_or_storage(bank, monkeypatch):
    service, session, repo, _, _ = bank
    before = repo.data_file.read_bytes()
    def fail(_):
        raise OSError("Injected disk failure")
    monkeypatch.setattr(repo, "_commit", fail)
    with pytest.raises(OSError):
        service.transfer(session, "1000 2200 7788", 50)
    assert session.account.get_balance() == 2450.75
    assert repo.data_file.read_bytes() == before


def test_daily_limit_persists_and_resets_at_stockholm_midnight(bank):
    service, session, repo, gateway, now = bank
    now[0] = datetime(2026, 10, 29, 22, 0, tzinfo=timezone.utc)
    service.withdraw(session, 600)
    session = gateway.insert("4556123412341234", "1234")
    service.withdraw(session, 400)
    with pytest.raises(ValueError, match="Daily"):
        service.withdraw(session, 0.01)
    now[0] = datetime(2026, 10, 29, 23, 0, tzinfo=timezone.utc)
    assert service.withdraw(session, 1)["amount"] == 1


def test_fee_checks_available_funds(bank):
    service, session, repo, _, _ = bank
    account = repo.find_by_account_number(session.account.account_number)
    account._balance = -100
    repo.save(account)
    with pytest.raises(ValueError, match="including"):
        service.transfer(session, "1000 2200 7788", 200)


def test_scheduled_payment_executes_once_and_failure_is_retained(bank):
    service, session, repo, gateway, now = bank
    service.schedule_payment(session, "1000 2200 7788", 50, "2026-10-30", "Årsavgift")
    service.schedule_payment(session, "1000 2200 7788", 5000, "2026-10-30", "Unavailable")
    assert service.process_due_payments(session) == []
    now[0] += timedelta(days=1)
    results = service.process_due_payments(session)
    assert [p["status"] for p in results] == ["executed", "failed"]
    session = gateway.insert("4556123412341234", "1234")
    assert service.process_due_payments(session) == []
    assert service.get_balance(session)["amount"] == 2400.75


def test_scheduled_commit_failure_rolls_back_all_changes(bank, monkeypatch):
    service, session, repo, _, now = bank
    service.schedule_payment(session, "1000 2200 7788", 50, "2026-10-29")
    before = repo.data_file.read_bytes()
    def fail(_):
        raise OSError("Disk unavailable")
    monkeypatch.setattr(repo, "_commit", fail)
    with pytest.raises(OSError):
        service.process_due_payments(session)
    assert repo.data_file.read_bytes() == before
    assert session.account._scheduled_payments[0]["status"] == "due"
    assert session.account.get_balance() == 2450.75


def test_history_filters_and_text_statement(bank):
    service, session, _, _, now = bank
    service.deposit(session, 10, "October")
    now[0] += timedelta(days=1)
    service.withdraw(session, 5, "Coffee")
    assert len(service.history(session, "2026-10-29", "2026-10-29")) == 1
    assert service.history(session, kind="WITHDRAWAL")[0]["note"] == "Coffee"
    assert len(service.history(session, query="October")) == 1
    assert "Fixture Customer" in service.export_statement(session, "text")
    with pytest.raises(ValueError):
        service.history(session, "2026-11-01", "2026-10-01")


@pytest.mark.parametrize("account_type,withdraw_fee,transfer_fee", [("Current", 0, 0), ("Savings", 1, 2), ("Premium", 0, 0)])
def test_account_policies_and_statement_renderers(bank, account_type, withdraw_fee, transfer_fee):
    service, session, repo, gateway, _ = bank
    rows = json.loads(repo.data_file.read_text(encoding="utf-8"))
    rows[0]["account_type"] = account_type
    repo.data_file.write_text(json.dumps(rows), encoding="utf-8")
    session = gateway.insert("4556123412341234", "1234")
    assert service.quote_fee(session, "withdraw", 50)["fee"] == withdraw_fee
    assert service.quote_fee(session, "transfer", 50)["fee"] == transfer_fee
    assert service.deposit(session, 50)["fee"] == 0
    assert service.export_statement(session).startswith("Date,Reference")
    assert account_type in service.export_statement(session, "text")


def test_pin_change_and_block_invalidate_other_sessions(bank):
    service, session, repo, gateway, _ = bank
    other = gateway.insert("4556123412341234", "1234")
    service.change_pin(session, "1234", "5678")
    assert not session.active
    with pytest.raises(ValueError, match="invalidated"):
        service.get_balance(other)
    with pytest.raises(ValueError):
        gateway.insert("4556123412341234", "1234")
    fresh = gateway.insert("4556123412341234", "5678")
    service.block_card(fresh)
    with pytest.raises(ValueError, match="blocked"):
        gateway.insert("4556123412341234", "5678")


def test_csv_quotes_multiline_descriptions_and_swedish_characters(bank):
    service, session, _, _, _ = bank
    note = 'Årsavgift; "Göteborg", café\nSecond line'
    service.deposit(session, 12.5, note)
    for locale, delimiter in [("en", ","), ("sv", ";")]:
        rows = list(csv.DictReader(io.StringIO(service.export_statement(session, locale=locale)), delimiter=delimiter))
        assert len(rows) == 1
        assert rows[0]["Description"] == note
        assert len(rows[0]) == 6


def test_statement_date_matches_local_history_filter_for_utc_transfers(bank):
    service, session, _, _, now = bank
    now[0] = datetime(2026, 10, 29, 23, 30, tzinfo=timezone.utc)
    service.transfer(session, "1000 2200 7788", 50)
    rows = list(csv.DictReader(io.StringIO(service.export_statement(session, start="2026-10-30", end="2026-10-30"))))
    assert len(rows) == 1
    assert rows[0]["Date"] == "2026-10-30"
