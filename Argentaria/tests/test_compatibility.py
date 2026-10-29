"""Reference CSV import conventions, not a claim to automate Excel itself."""
import csv
import io
from datetime import date
from decimal import Decimal

import pytest

from test_operations import bank


def test_english_numeric_csv_round_trip(bank):
    service, session, _, _, _ = bank
    service.deposit(session, 12.5, "Södra Vägen; café")
    rows = list(csv.DictReader(io.StringIO(service.export_statement(session))))
    assert Decimal(rows[0]["Amount EUR"]) == Decimal("12.50")
    assert Decimal(rows[0]["Balance EUR"]) == Decimal("2463.25")
    assert date.fromisoformat(rows[0]["Date"]).isoformat() == "2026-10-29"


@pytest.mark.xfail(strict=True, reason="COMP-A1: Swedish export uses decimal point rather than decimal comma")
def test_swedish_numeric_csv_round_trip(bank):
    service, session, _, _, _ = bank
    service.deposit(session, 12.5, "Göteborg")
    row = list(csv.DictReader(io.StringIO(service.export_statement(session, locale="sv")), delimiter=";"))[0]
    imported = Decimal(row["Amount EUR"].replace(".", "").replace(",", "."))
    assert imported == Decimal("12.50")


@pytest.mark.xfail(strict=True, reason="COMP-A2: Swedish export date differs from documented ISO date convention")
def test_swedish_date_csv_round_trip(bank):
    service, session, _, _, _ = bank
    service.deposit(session, 12.5)
    row = list(csv.DictReader(io.StringIO(service.export_statement(session, locale="sv")), delimiter=";"))[0]
    assert row["Date"] == "2026-10-29"
