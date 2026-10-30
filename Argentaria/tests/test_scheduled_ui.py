import json
from types import SimpleNamespace

import pytest

tk = pytest.importorskip("tkinter")

from test_operations import bank
from ui.scheduled_payments import ScheduledPaymentsView
from ui.tk_app import ArgentariaApp


@pytest.fixture
def desktop(bank, monkeypatch):
    _, _, repository, _, now = bank
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tk display is unavailable")
    root.withdraw()
    monkeypatch.setattr(tk, "Tk", lambda: root)
    answers = [True]
    questions, messages = [], []

    def confirm(title, text, **kwargs):
        questions.append(text)
        return answers[-1]

    monkeypatch.setattr("ui.scheduled_payments.messagebox.askyesno", confirm)
    monkeypatch.setattr("ui.scheduled_payments.messagebox.showinfo", lambda title, text, **kw: messages.append(("info", text)))
    monkeypatch.setattr("ui.scheduled_payments.messagebox.showerror", lambda title, text, **kw: messages.append(("error", text)))
    app = ArgentariaApp(repository.data_file)
    app.banking.clock = lambda: now[0]
    app.session = app.gateway.insert("4556123412341234", "1234")

    def render():
        app.show_scheduled()
        root.geometry("900x620+10000+10000")
        root.deiconify()
        root.update()
        return next(child for child in app.content.winfo_children() if isinstance(child, ScheduledPaymentsView))

    try:
        yield SimpleNamespace(app=app, repository=repository, render=render, root=root,
                              answers=answers, questions=questions, messages=messages)
    finally:
        root.destroy()


def test_selected_future_payment_confirms_costs_updates_table_and_records_activity(desktop):
    app = desktop.app
    payment = app.banking.schedule_payment(app.session, "1000 2200 7788", 200, "2027-10-29")
    view = desktop.render()
    assert "disabled" in view.selected_button.state()
    assert view.table.set(payment["id"], "status") == "pending"
    view.table.selection_set(payment["id"])
    desktop.root.update()
    assert "disabled" not in view.selected_button.state()
    view.selected_button.invoke()
    desktop.root.update()
    assert "paid immediately" in desktop.questions[0]
    assert "fee EUR 0.50" in desktop.questions[0]
    assert "Total debit if all succeed: EUR 200.50" in desktop.questions[0]
    assert view.table.set(payment["id"], "status") == "executed"
    assert view.table.set(payment["id"], "fee") == "0.50"
    assert view.table.set(payment["id"], "total") == "200.50"
    assert view.table.set(payment["id"], "result")
    assert "disabled" in view.selected_button.state()
    assert app.session.account.get_balance() == 2250.25
    assert "New balance: EUR 2250.25" in desktop.messages[-1][1]
    assert desktop.repository.find_by_account_number("1000 2200 7788").get_balance() == 8320
    events = json.loads(app.activity_log.to_json())["events"]
    result = next(row for row in events if row["action"] == "banking.process_scheduled_payments")
    assert result["request"]["payment_ids"] == [payment["id"]]
    assert result["response"][0]["total_debited"] == 200.5


def test_multi_selection_cancellation_changes_no_balances_or_statuses(desktop):
    app = desktop.app
    payments = [app.banking.schedule_payment(app.session, "1000 2200 7788", amount, "2027-10-29") for amount in [50, 200]]
    view = desktop.render()
    view.table.selection_set([payment["id"] for payment in payments])
    desktop.root.update()
    desktop.answers[:] = [False]
    before = desktop.repository.data_file.read_bytes()
    view.selected_button.invoke()
    assert "Total amount: EUR 250.00" in desktop.questions[0]
    assert "Total fees: EUR 0.50" in desktop.questions[0]
    assert desktop.repository.data_file.read_bytes() == before
    assert all(view.table.set(payment["id"], "status") == "pending" for payment in payments)
    assert desktop.messages == []
    assert any(row["action"] == "confirmation.cancel" for row in json.loads(app.activity_log.to_json())["events"])


def test_due_action_ignores_selected_future_rows_and_reports_no_due_payments(desktop):
    app = desktop.app
    future = app.banking.schedule_payment(app.session, "1000 2200 7788", 50, "2027-10-29")
    today = app.banking.schedule_payment(app.session, "1000 2200 7788", 25, "2026-10-29")
    view = desktop.render()
    view.table.selection_set(future["id"])
    desktop.root.update()
    view.process(False)
    assert view.table.set(today["id"], "status") == "executed"
    assert view.table.set(future["id"], "status") == "pending"
    assert "Only payments due today or earlier" in desktop.questions[0]
    assert app.session.account.get_balance() == 2425.75
    view.process(False)
    assert desktop.messages[-1] == ("info", "No pending payments are due yet.")


def test_failed_selected_payment_shows_zero_charges_and_cannot_be_reselected(desktop):
    app = desktop.app
    payment = app.banking.schedule_payment(app.session, "1000 2200 7788", 5000, "2027-10-29")
    view = desktop.render()
    view.table.selection_set(payment["id"])
    desktop.root.update()
    view.selected_button.invoke()
    assert view.table.set(payment["id"], "status") == "failed"
    assert view.table.set(payment["id"], "fee") == view.table.set(payment["id"], "total") == "0.00"
    assert "Insufficient" in view.table.set(payment["id"], "result")
    view.table.selection_set(payment["id"])
    desktop.root.update()
    assert "disabled" in view.selected_button.state()
    assert "Executed: 0 · Failed: 1" in desktop.messages[-1][1]
    assert app.session.account.get_balance() == 2450.75
