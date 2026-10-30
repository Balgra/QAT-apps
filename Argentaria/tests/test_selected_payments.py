from concurrent.futures import ThreadPoolExecutor
import json

import pytest

from services.activity_log import ActivityLog
from test_operations import bank


DESTINATION = "1000 2200 7788"
FUTURE = "2027-10-29"


def test_selected_future_payment_records_actual_costs_and_linked_transactions(bank):
    service, session, repo, _, now = bank
    service.activity_log = ActivityLog()
    payment = service.schedule_payment(session, DESTINATION, 200, FUTURE, "Årsavgift")
    quote = service.preview_scheduled_payments(session, [payment["id"]])
    assert quote["amount"] == 200 and quote["fee"] == 0.5 and quote["total_debited"] == 200.5
    result = service.process_scheduled_payments(session, [payment["id"]], expected_payments=quote["payments"])[0]
    assert result["status"] == "executed" and result["due_date"] == FUTURE
    assert result["fee"] == 0.5 and result["total_debited"] == 200.5
    assert result["processed_at"] == now[0].isoformat()
    assert result["balance"] == session.account.get_balance() == 2250.25
    source = repo.find_by_account_number(session.account.account_number)
    destination = repo.find_by_account_number(DESTINATION)
    sent = next(row for row in source._transactions if row.kind == "TRANSFER_OUT")
    received = next(row for row in destination._transactions if row.kind == "TRANSFER_IN")
    fee = next(row for row in source._transactions if row.kind == "FEE")
    assert sent.transaction_id == received.transaction_id == result["transaction_id"]
    assert sent.amount == received.amount == 200
    assert fee.amount == 0.5 and result["transaction_id"] in fee.note
    assert destination.get_balance() == 8320
    assert source._scheduled_payments[0] == result
    recorded = json.loads(service.activity_log.to_json())["events"]
    processed = next(row for row in recorded if row["action"] == "banking.process_scheduled_payments")
    assert processed["request"]["payment_ids"] == [payment["id"]]
    assert processed["response"][0] == result


def test_only_selected_payments_execute_and_normal_due_processing_still_skips_future(bank):
    service, session, repo, _, _ = bank
    payments = [service.schedule_payment(session, DESTINATION, amount, FUTURE) for amount in [10, 20, 30]]
    assert service.preview_scheduled_payments(session)["payments"] == []
    assert service.process_due_payments(session) == []
    result = service.process_scheduled_payments(session, [payments[0]["id"], payments[2]["id"]])
    assert [row["id"] for row in result] == [payments[0]["id"], payments[2]["id"]]
    assert [row["status"] for row in service.scheduled_payments(session)] == ["executed", "due", "executed"]
    assert repo.find_by_account_number(DESTINATION).get_balance() == 8160
    assert session.account.get_balance() == 2410.75


@pytest.mark.parametrize("amount,fee", [(0.01, 0), (100, 0), (100.01, 0.5), (5000, 0.5)])
def test_selected_amount_and_current_fee_boundaries(bank, amount, fee):
    service, session, repo, gateway, _ = bank
    account = repo.find_by_account_number(session.account.account_number)
    account._balance = 6000
    repo.save(account)
    session = gateway.insert("4556123412341234", "1234")
    payment = service.schedule_payment(session, DESTINATION, amount, FUTURE)
    result = service.process_scheduled_payments(session, [payment["id"]])[0]
    assert result["fee"] == fee
    assert result["total_debited"] == round(amount + fee, 2)
    assert result["balance"] == round(6000 - amount - fee, 2)


@pytest.mark.parametrize("selection", [None, [], "reference", ["missing"], [""], [123], [True]])
def test_invalid_selection_does_not_change_accounts(bank, selection):
    service, session, repo, _, _ = bank
    before = repo.data_file.read_bytes()
    with pytest.raises(ValueError):
        service.process_scheduled_payments(session, selection)
    assert repo.data_file.read_bytes() == before


def test_duplicate_unknown_and_other_account_references_are_rejected_as_a_batch(bank):
    service, session, repo, gateway, _ = bank
    own = service.schedule_payment(session, DESTINATION, 50, FUTURE)
    other_session = gateway.insert("4556123412349876", "4321")
    other = service.schedule_payment(other_session, session.account.account_number, 50, FUTURE)
    for selection in [[own["id"], own["id"]], [own["id"], "missing"], [other["id"]]]:
        before = repo.data_file.read_bytes()
        with pytest.raises(ValueError):
            service.process_scheduled_payments(session, selection)
        assert repo.data_file.read_bytes() == before


def test_completed_or_failed_payment_cannot_be_charged_again(bank):
    service, session, repo, _, _ = bank
    successful = service.schedule_payment(session, DESTINATION, 50, FUTURE)
    failed = service.schedule_payment(session, DESTINATION, 5000, FUTURE)
    results = service.process_scheduled_payments(session, [successful["id"], failed["id"]])
    assert [row["status"] for row in results] == ["executed", "failed"]
    assert results[1]["fee"] == results[1]["total_debited"] == 0
    before = repo.data_file.read_bytes()
    for payment in results:
        with pytest.raises(ValueError, match="Only pending"):
            service.process_scheduled_payments(session, [payment["id"]])
    assert repo.data_file.read_bytes() == before


def test_insufficient_funds_including_fee_is_rejected_and_other_selection_can_succeed(bank):
    service, session, repo, _, _ = bank
    account = repo.find_by_account_number(session.account.account_number)
    account._balance = 200
    account.overdraft = 0
    repo.save(account)
    large = service.schedule_payment(session, DESTINATION, 200, FUTURE)
    small = service.schedule_payment(session, DESTINATION, 50, FUTURE)
    results = service.process_scheduled_payments(session, [large["id"], small["id"]])
    assert [row["status"] for row in results] == ["failed", "executed"]
    assert "including" in results[0]["error"]
    assert results[0]["fee"] == results[0]["total_debited"] == 0
    assert session.account.get_balance() == 150
    assert repo.find_by_account_number(DESTINATION).get_balance() == 8170


@pytest.mark.parametrize("change", ["fee", "amount", "destination", "note"])
def test_changed_payment_details_or_fees_require_new_confirmation(bank, change):
    service, session, repo, _, _ = bank
    payment = service.schedule_payment(session, DESTINATION, 50, FUTURE)
    quoted = service.preview_scheduled_payments(session, [payment["id"]])["payments"]
    with repo.transaction() as accounts:
        source = next(account for account in accounts if account.account_number == session.account.account_number)
        if change == "fee":
            source.account_type = "Savings"
        else:
            replacement = {"amount": 75, "destination": "1000 2200 3344", "note": "Changed"}[change]
            source._scheduled_payments[0][change] = replacement
    before = repo.data_file.read_bytes()
    with pytest.raises(ValueError, match="changed"):
        service.process_scheduled_payments(session, [payment["id"]], expected_payments=quoted)
    assert repo.data_file.read_bytes() == before


def test_commit_failure_rolls_back_selected_transfers_fees_and_statuses(bank, monkeypatch):
    service, session, repo, _, _ = bank
    selected = [service.schedule_payment(session, DESTINATION, amount, FUTURE)["id"] for amount in [200, 50]]
    before = repo.data_file.read_bytes()

    def fail(_):
        raise OSError("Disk unavailable")

    monkeypatch.setattr(repo, "_commit", fail)
    with pytest.raises(OSError, match="Disk"):
        service.process_scheduled_payments(session, selected)
    assert repo.data_file.read_bytes() == before
    assert session.account.get_balance() == 2450.75
    assert all(row["status"] == "due" for row in session.account._scheduled_payments)


def test_late_validation_failure_does_not_leave_a_partial_transfer(bank, monkeypatch):
    service, session, repo, _, _ = bank
    payment = service.schedule_payment(session, DESTINATION, 200, FUTURE)

    def fail_after_transfer(*_):
        raise ValueError("Injected fee error")

    monkeypatch.setattr(service.fee_processor, "apply", fail_after_transfer)
    result = service.process_scheduled_payments(session, [payment["id"]])[0]
    assert result["status"] == "failed"
    assert result["fee"] == result["total_debited"] == 0
    assert session.account.get_balance() == 2450.75
    assert repo.find_by_account_number(DESTINATION).get_balance() == 8120
    assert service.history(session) == []


def test_concurrent_attempts_charge_a_selected_payment_only_once(bank):
    service, session, repo, _, _ = bank
    payment = service.schedule_payment(session, DESTINATION, 200, FUTURE)

    def attempt(_):
        try:
            return service.process_scheduled_payments(session, [payment["id"]])[0]["status"]
        except ValueError:
            return "rejected"

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(attempt, range(2))) == ["executed", "rejected"]
    assert repo.find_by_account_number(session.account.account_number).get_balance() == 2250.25
    assert repo.find_by_account_number(DESTINATION).get_balance() == 8320


def test_processing_requires_an_active_current_card_session(bank):
    service, session, repo, _, _ = bank
    payment = service.schedule_payment(session, DESTINATION, 50, FUTURE)
    before = repo.data_file.read_bytes()
    session.close()
    with pytest.raises(ValueError):
        service.process_scheduled_payments(session, [payment["id"]])
    with pytest.raises(ValueError):
        service.preview_scheduled_payments(None, [payment["id"]])
    assert repo.data_file.read_bytes() == before
