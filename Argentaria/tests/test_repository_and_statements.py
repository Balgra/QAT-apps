import csv
import io
from datetime import datetime, timedelta, timezone

import pytest

from repository import AccountRepository
from services.banking_service import BankingService
from services.currency_service import CurrencyService
from test_operations import bank


def test_repository_queries_and_status_updates(bank):
    _, _, repo, _, _ = bank
    assert repo.find_by_card("4556 1234 1234 1234").account_number == "1000 2200 3344"
    assert repo.find_by_card("unknown") is None
    assert repo.find_by_account_number("100022007788").account_type == "Savings"
    assert repo.find_by_account_number("unknown") is None
    repo.update_card_status("4556123412341234", "blocked")
    fresh = AccountRepository(repo.data_file)
    assert fresh.find_by_card("4556123412341234").card.status == "blocked"
    assert fresh.find_by_card("4556123412349876").card.status == "active"


def test_real_commit_failure_preserves_file_and_cleans_temporary_file(bank, monkeypatch):
    service, session, repo, _, _ = bank
    before = repo.data_file.read_bytes()
    def fail(source, destination):
        raise OSError("Injected atomic replacement failure")
    monkeypatch.setattr("repository.account_repository.os.replace", fail)
    with pytest.raises(OSError):
        service.deposit(session, 20)
    assert repo.data_file.read_bytes() == before
    assert session.account.get_balance() == 2450.75
    assert not list(repo.data_file.parent.glob("argentaria-*.tmp"))


def test_repository_transaction_exception_does_not_persist(bank):
    _, _, repo, _, _ = bank
    before = repo.data_file.read_bytes()
    with pytest.raises(ValueError):
        with repo.transaction() as accounts:
            accounts[0]._balance = 0
            raise ValueError("Business operation rejected")
    assert repo.data_file.read_bytes() == before


@pytest.mark.parametrize("format,locale", [("xml", "en"), ("csv", "unknown")])
def test_unknown_statement_options_are_rejected(bank, format, locale):
    service, session, _, _, _ = bank
    with pytest.raises(ValueError):
        service.export_statement(session, format, locale)


def test_history_inclusive_boundaries_filter_and_order(bank):
    service, session, _, _, now = bank
    for day, amount, note in [(28, 1, "Before"), (29, 2, "At start"), (30, 3, "At end"), (31, 4, "After")]:
        now[0] = datetime(2026, 10, day, 12, tzinfo=timezone.utc)
        service.deposit(session, amount, note)
    asc = service.history(session, "2026-10-29", "2026-10-30", order="ascending")
    assert [r["amount"] for r in asc] == [2, 3]
    assert [r["amount"] for r in service.history(session, "2026-10-29", "2026-10-30")] == [3, 2]
    assert service.history(session, query="not-present") == []
    assert len(service.history(session, query=asc[0]["transaction_id"].lower())) == 1
    assert service.history(session, kind="WITHDRAWAL") == []
    with pytest.raises(ValueError):
        service.history(session, order="random")


def test_history_stable_ties_and_legacy_local_timestamps(bank):
    service, session, repo, _, now = bank
    for amount in [1, 2, 3]:
        service.deposit(session, amount)
    assert [r["amount"] for r in service.history(session)] == [3, 2, 1]
    assert [r["amount"] for r in service.history(session, order="ascending")] == [1, 2, 3]
    account = repo.find_by_card("4556123412341234")
    account.get_transactions()[0].timestamp = "2026-10-29T23:59:59"
    repo.save(account)
    assert len(service.history(session, "2026-10-29", "2026-10-29")) == 3
    service.withdraw(session, 1)  # Daily calculation also accepts the legacy naive timestamp.


@pytest.mark.parametrize("account_type", ["Current", "Savings", "Premium"])
@pytest.mark.parametrize("locale,delimiter", [("en", ","), ("sv", ";")])
def test_csv_all_subtypes_preserve_signed_rows_notes_and_historical_balances(bank, account_type, locale, delimiter):
    from test_bank_boundaries import configure
    service, _, _, _, _ = bank
    session = configure(bank, account_type, balance=10000)
    service.deposit(session, 20, 'Årsavgift; "quoted", café\nnew line')
    service.withdraw(session, 10, "Cash")
    service.transfer(session, "1000 2200 7788", 50, "Transfer")
    expected = service.history(session)
    rows = list(csv.DictReader(io.StringIO(service.export_statement(session, locale=locale)), delimiter=delimiter))
    assert len(rows) == len(expected)
    for exported, original in zip(rows, expected):
        sign = -1 if original["kind"] in {"WITHDRAWAL", "TRANSFER_OUT", "FEE"} else 1
        # Check the written number, separately from the intentional Swedish import-convention exercise.
        assert float(exported["Amount EUR"]) == sign * original["amount"]
        assert float(exported["Balance EUR"]) == original["balance_after"]
        assert exported["Description"] == original["note"]
    text = service.export_statement(session, "text")
    assert account_type in text and "USD" in text and "SEK" in text and "Transfer" in text


def test_statement_export_is_complete_beyond_dashboard_limit_and_filters(bank):
    service, session, _, _, _ = bank
    for index in range(12):
        service.deposit(session, index + 1, f"Entry {index}")
    assert len(service.account_details(session)["transactions"]) == 8
    all_rows = list(csv.DictReader(io.StringIO(service.export_statement(session))))
    assert len(all_rows) == 12
    rows = list(csv.DictReader(io.StringIO(service.export_statement(session, query="Entry 10"))))
    assert len(rows) == 1 and rows[0]["Amount EUR"] == "11.00"


def test_empty_statement_exports_a_header_and_no_transactions(bank):
    service, session, _, _, _ = bank
    assert list(csv.DictReader(io.StringIO(service.export_statement(session)))) == []


def test_legacy_statement_includes_requested_sections(bank):
    service, session, _, _, _ = bank
    service.deposit(session, 5, "Example")
    details = service.account_details(session)
    full = service.prepare_statement(session, False, True, True, True, "descending", "", "", "HEADER", "FOOTER")
    assert full[0] == "HEADER" and full[-1] == "FOOTER"
    assert details["address"] in full and details["card"] in full
    assert any(line.startswith("USD ") for line in full)
    assert any("DEPOSIT 5.00" in line for line in full)
    short = service.prepare_statement(session, False, False, False, False, "descending", "", "", "HEADER", "FOOTER")
    assert details["address"] not in short and details["card"] not in short
    # Unimplemented legacy filtering parameters are intentionally not pinned as required behavior.


def test_card_status_or_missing_account_invalidates_existing_session(bank):
    service, session, repo, gateway, _ = bank
    repo.update_card_status("4556123412341234", "blocked")
    with pytest.raises(ValueError):
        service.get_balance(session)
    assert not session.active
    repo.update_card_status("4556123412341234", "active")
    session = gateway.insert("4556123412341234", "1234")
    with repo.transaction() as accounts:
        accounts[:] = [a for a in accounts if a.account_number != session.account.account_number]
    with pytest.raises(ValueError):
        service.get_balance(session)
    assert not session.active


def test_unknown_fee_operation_rejected(bank):
    with pytest.raises(ValueError):
        bank[0].quote_fee(bank[1], "unknown", 50)


@pytest.mark.parametrize("account_type", ["Current", "Savings", "Premium"])
def test_csv_accepts_legacy_local_timestamp_for_every_account_type(bank, account_type):
    from test_bank_boundaries import configure
    service, _, repo, _, _ = bank
    session = configure(bank, account_type)
    service.deposit(session, 1)
    account = repo.find_by_card("4556123412341234")
    account.get_transactions()[0].timestamp = "2026-10-29T23:59:59"
    repo.save(account)
    rows = list(csv.DictReader(io.StringIO(service.export_statement(session))))
    assert rows[0]["Date"] == "2026-10-29"
