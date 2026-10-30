from concurrent.futures import ThreadPoolExecutor
import inspect
import json

import pytest

from services.activity_log import ActivityLog, REDACTED
from test_operations import bank


def test_operations_capture_inputs_results_and_errors_without_changing_them(bank):
    service, session, _, gateway, _ = bank
    activity = ActivityLog()
    service.activity_log = gateway.activity_log = activity
    with pytest.raises(ValueError, match="Incorrect PIN"):
        gateway.insert("4556123412341234", "0000")
    assert gateway.insert("4556123412341234", "1234").active
    balance = service.get_balance(session, "USD")
    deposit = service.deposit(session, 20, "Göteborg café")
    with pytest.raises(ValueError, match="positive"):
        service.withdraw(session, -1)
    events = json.loads(activity.to_json())["events"]
    assert [row["action"] for row in events] == ["card.insert", "card.insert", "banking.get_balance", "banking.deposit", "banking.withdraw"]
    assert events[0]["error"]["type"] == "ValueError"
    assert events[0]["request"]["card_number"] == events[0]["request"]["pin"] == REDACTED
    assert events[1]["response"] == {"type": "CardSession"}
    assert events[2]["response"] == balance
    assert events[3]["request"]["note"] == "Göteborg café"
    assert events[3]["response"] == deposit
    assert events[4]["request"]["amount"] == -1
    assert all(row["duration_ms"] >= 0 for row in events)
    assert "4556123412341234" not in activity.to_json()


def test_pin_changes_redact_all_pin_fields_and_keep_the_actual_result(bank):
    service, session, _, gateway, _ = bank
    activity = ActivityLog()
    service.activity_log = gateway.activity_log = activity
    service.change_pin(session, "1234", "5678")
    assert session.active is False
    assert gateway.insert("4556123412341234", "5678").active
    request = json.loads(activity.to_json())["events"][0]["request"]
    assert request["old_pin"] == request["new_pin"] == REDACTED
    assert '"5678"' not in activity.to_json() and '"1234"' not in activity.to_json()


def test_exports_keep_nested_results_detached_and_preserve_international_text(bank, tmp_path):
    service, session, _, _, _ = bank
    activity = ActivityLog()
    service.activity_log = activity
    payment = service.schedule_payment(session, "1000 2200 7788", 20, "2026-10-30", "Göteborg")
    payment["note"] = "changed outside logger"
    statement = service.export_statement(session)
    output = tmp_path / "activity.json"
    activity.export(output)
    document = json.loads(output.read_text(encoding="utf-8"))
    assert document["application"] == "Argentaria"
    scheduled = next(row for row in document["events"] if row["action"] == "banking.schedule_payment")
    exported = next(row for row in document["events"] if row["action"] == "banking.export_statement")
    assert scheduled["response"]["note"] == "Göteborg"
    assert exported["response"] == statement
    assert "changed outside logger" not in output.read_text(encoding="utf-8")


def test_invalid_nonfinite_amount_is_logged_as_an_error_with_valid_json(bank):
    service, session, _, _, _ = bank
    service.activity_log = ActivityLog()
    with pytest.raises(ValueError):
        service.deposit(session, float("nan"))
    row = json.loads(service.activity_log.to_json())["events"][0]
    assert row["request"]["amount"] == "nan"
    assert row["error"]["type"] == "ValueError"


def test_concurrent_records_export_without_loss_and_logs_start_empty(tmp_path):
    activity = ActivityLog()
    assert json.loads(activity.to_json())["events"] == []
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda n: activity.record("navigation", {"view": n}), range(20)))
    document = json.loads(activity.to_json())
    assert [row["sequence"] for row in document["events"]] == list(range(1, 21))
    assert {row["request"]["view"] for row in document["events"]} == set(range(20))
    other = ActivityLog()
    assert other.session_id != activity.session_id
    assert json.loads(other.to_json())["events"] == []
    with pytest.raises(OSError):
        activity.export(tmp_path)


def test_service_signatures_and_default_behavior_remain_available(bank):
    service, session, _, _, _ = bank
    assert service.activity_log is None
    assert list(inspect.signature(service.deposit).parameters) == ["session", "amount", "note"]
    assert service.deposit(session, 1)["amount"] == 1


def test_failed_export_preserves_the_previous_download_and_cleans_temporary_files(tmp_path, monkeypatch):
    destination = tmp_path / "previous.json"
    destination.write_text('{"previous": true}', encoding="utf-8")
    activity = ActivityLog()
    activity.record("navigation", {"view": "Overview"})

    def failed_replace(source, target):
        raise OSError("Simulated save failure")

    monkeypatch.setattr("services.activity_log.os.replace", failed_replace)
    with pytest.raises(OSError, match="Simulated save failure"):
        activity.export(destination)
    assert json.loads(destination.read_text(encoding="utf-8")) == {"previous": True}
    assert list(tmp_path.iterdir()) == [destination]
    assert len(json.loads(activity.to_json())["events"]) == 1
