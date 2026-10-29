from __future__ import annotations

from datetime import datetime, date, timezone
from uuid import uuid4
from zoneinfo import ZoneInfo

from repository import AccountRepository
from .currency_service import CurrencyService
from .transaction_processors import CashDepositProcessor, CashWithdrawalProcessor
from .operations import TransferProcessor, FeeProcessor, amount_value


class AuditRelay:
    def write(self, account, action: str) -> None:
        account._last_audit_message = f"{datetime.now().isoformat(timespec='seconds')}:{action}"


class BankingService:
    def __init__(self, repository: AccountRepository, currency_service: CurrencyService, clock=None):
        self.repository = repository
        self.currency_service = currency_service
        self.deposit_processor = CashDepositProcessor()
        self.withdrawal_processor = CashWithdrawalProcessor()
        self.audit_relay = AuditRelay()
        self.terminal_id = "GOT-ATM-04"
        self.location = "Gothenburg Central"
        self.operator = "SELF-SERVICE"
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.fee_processor = FeeProcessor()
        self.transfer_processor = TransferProcessor()

    def get_balance(self, session, display_currency: str = "EUR") -> dict:
        if session is None or not session.active:
            raise ValueError("Insert a card first")
        account = self._fresh(session)
        euro = account.get_balance()
        converted = self.currency_service.convert(euro, display_currency)
        self.audit_relay.write(account, "BALANCE_VIEW")
        return {"amount": converted, "currency": display_currency, "symbol": self.currency_service.label_for(display_currency), "base_amount": euro}

    def deposit(self, session, amount: float, note: str = "") -> dict:
        return self._cash(session, amount, note, "deposit")

    def withdraw(self, session, amount: float, note: str = "") -> dict:
        return self._cash(session, amount, note, "withdraw")

    def account_details(self, session) -> dict:
        if session is None or not session.active:
            raise ValueError("Insert a card first")
        account = self._fresh(session)
        customer = account.get_card().get_customer()
        address = account.get_card().get_customer().get_profile().get_address().formatted()
        balance = account.get_balance()
        details = {
            "holder": customer.full_name,
            "email": customer.profile.email,
            "phone": customer.profile.phone,
            "address": address,
            "account_number": account.account_number,
            "iban": account.iban,
            "account_type": account.account_type,
            "card": account.card.masked_number(),
            "balance_eur": balance,
            "balance_usd": round(balance * 1.1, 2),
            "balance_sek": round(balance * 9.5, 2),
            "transactions": [item.as_dict() for item in account.get_transactions()[:8]],
        }
        if account.account_type == "Savings":
            details["account_feature"] = f"Monthly interest estimate: €{account.calculate_monthly_interest():,.2f}"
        elif account.account_type in {"Current", "Premium"}:
            details["account_feature"] = f"Overdraft available: €{account.overdraft_limit():,.2f}"
        else:
            details["account_feature"] = "Standard account"
        self.audit_relay.write(account, "DETAILS_VIEW")
        return details

    def prepare_statement(self, session, include_pending: bool, include_address: bool, include_card: bool, include_conversion: bool, sort_order: str, start_date: str, end_date: str, heading: str, footer: str) -> list[str]:
        details = self.account_details(session)
        lines = [heading, details["holder"], details["iban"]]
        if include_address:
            lines.append(details["address"])
        if include_card:
            lines.append(details["card"])
        if include_conversion:
            lines.extend([f"USD {details['balance_usd']}", f"SEK {details['balance_sek']}"])
        for item in details["transactions"]:
            lines.append(f"{item['timestamp']} {item['kind']} {item['amount']:.2f}")
        lines.append(footer)
        return lines

    def _fresh(self, session, accounts=None):
        if session is None or not session.active:
            raise ValueError("Insert a card first")
        snapshot = session.get_account()
        selected = accounts if accounts is not None else self.repository.get_all()
        account = next((a for a in selected if a.account_number == snapshot.account_number), None)
        if account is None or account.card.status != "active" or account.card._pin != snapshot.card._pin:
            session.close()
            raise ValueError("Session invalidated; insert an active card again")
        return account

    def quote_fee(self, session, operation, amount):
        account = self._fresh(session)
        if operation not in {"deposit", "withdraw", "transfer"}:
            raise ValueError("Unknown cash operation")
        amount = amount_value(amount)
        fee = self.fee_processor.quote(account, operation, amount)
        return {"amount": amount, "fee": fee, "total": round(amount + fee, 2)}

    def _cash(self, session, value, note, operation):
        amount = amount_value(value)
        with self.repository.transaction() as accounts:
            account = self._fresh(session, accounts)
            fee = self.fee_processor.quote(account, operation, amount)
            now = self.clock().astimezone(ZoneInfo("Europe/Stockholm"))
            if operation == "withdraw":
                used = 0
                for item in account._transactions:
                    moment = datetime.fromisoformat(item.timestamp)
                    if moment.tzinfo is None:
                        moment = moment.replace(tzinfo=ZoneInfo("Europe/Stockholm"))
                    if item.kind == "WITHDRAWAL" and moment.astimezone(ZoneInfo("Europe/Stockholm")).date() == now.date():
                        used += item.amount
                if round(used + amount, 2) > 1000:
                    raise ValueError("Daily cash withdrawals are limited to EUR 1,000")
                if not account.can_withdraw(round(amount + fee, 2)):
                    raise ValueError("Insufficient funds including fee")
                processor = self.withdrawal_processor
            else:
                processor = self.deposit_processor
            transaction = processor.process(account, amount, self.repository, self.location, self.terminal_id,
                                            self.operator, operation, note, "EUR", True, now.isoformat(), False)
            self.fee_processor.apply(account, fee, now.isoformat(), transaction.transaction_id)
            self.audit_relay.write(account, operation.upper())
            result = {"transaction_id": transaction.transaction_id, "amount": amount, "fee": fee,
                      "balance": account.get_balance(), "kind": transaction.kind}
        session.account = account
        return result

    def _move(self, accounts, account, destination_number, value, note):
        amount = amount_value(value)
        destination = next((a for a in accounts if a.account_number.replace(" ", "") == destination_number.replace(" ", "")), None)
        if not destination:
            raise ValueError("Destination account was not found")
        fee = self.fee_processor.quote(account, "transfer", amount)
        if not account.can_withdraw(round(amount + fee, 2)):
            raise ValueError("Insufficient funds including transfer fee")
        timestamp = self.clock().isoformat()
        transaction = self.transfer_processor.process(account, destination, amount, self.repository, self.location,
                                                     self.terminal_id, self.operator, "TRANSFER", note, "EUR", True, timestamp)
        self.fee_processor.apply(account, fee, timestamp, transaction.transaction_id)
        return {"transaction_id": transaction.transaction_id, "amount": amount, "fee": fee,
                "balance": account.get_balance(), "destination": destination.account_number}

    def transfer(self, session, destination, amount, note=""):
        with self.repository.transaction() as accounts:
            account = self._fresh(session, accounts)
            result = self._move(accounts, account, destination, amount, note)
        session.account = account
        return result

    def history(self, session, start="", end="", kind="all", query="", order="descending"):
        account = self._fresh(session)
        start_date = date.fromisoformat(start) if start else date.min
        end_date = date.fromisoformat(end) if end else date.max
        if start_date > end_date:
            raise ValueError("Start date must precede end date")
        if order not in {"ascending", "descending"}:
            raise ValueError("Unknown sort order")
        rows = []
        for index, item in enumerate(account._transactions):
            moment = datetime.fromisoformat(item.timestamp)
            if moment.tzinfo:
                moment = moment.astimezone(ZoneInfo("Europe/Stockholm"))
            if start_date <= moment.date() <= end_date:
                if kind == "all" or item.kind == kind:
                    if not query or query.casefold() in (item.note + item.transaction_id).casefold():
                        rows.append((moment.replace(tzinfo=None), -index, item.as_dict()))
        rows.sort(key=lambda row: (row[0], row[1]), reverse=order == "descending")
        return [row[2] for row in rows]

    def export_statement(self, session, format="csv", locale="en", start="", end="", kind="all", query=""):
        from .statement_formats import CurrentStatement, SavingsStatement, PremiumStatement
        account = self._fresh(session)
        details = self.account_details(session)
        details["transactions"] = self.history(session, start, end, kind, query)
        if account.account_type == "Savings":
            renderer = SavingsStatement()
        elif account.account_type == "Premium":
            renderer = PremiumStatement()
        else:
            renderer = CurrentStatement()
        if locale not in {"en", "sv"}:
            raise ValueError("Choose English or Swedish import conventions")
        if format == "csv":
            return renderer.csv(details, locale)
        if format == "text":
            return renderer.text(details)
        raise ValueError("Choose CSV or text statement format")

    def schedule_payment(self, session, destination, amount, due_date, note=""):
        amount = amount_value(amount)
        due = date.fromisoformat(due_date)
        if due < self.clock().astimezone(ZoneInfo("Europe/Stockholm")).date():
            raise ValueError("Due date cannot be in the past")
        if amount > 5000:
            raise ValueError("Single scheduled payments are limited to EUR 5,000")
        with self.repository.transaction() as accounts:
            account = self._fresh(session, accounts)
            target = next((a for a in accounts if a.account_number.replace(" ", "") == destination.replace(" ", "")), None)
            if target is None or target.account_number == account.account_number:
                raise ValueError("Choose another known account")
            payment = {"id": uuid4().hex, "destination": target.account_number, "amount": amount,
                       "due_date": due.isoformat(), "note": note, "status": "due"}
            account._scheduled_payments.append(payment)
        session.account = account
        return payment

    def scheduled_payments(self, session):
        return self._fresh(session)._scheduled_payments

    def process_due_payments(self, session):
        today = self.clock().astimezone(ZoneInfo("Europe/Stockholm")).date().isoformat()
        with self.repository.transaction() as accounts:
            account = self._fresh(session, accounts)
            results = []
            for payment in account._scheduled_payments:
                if payment["status"] == "due" and payment["due_date"] <= today:
                    try:
                        result = self._move(accounts, account, payment["destination"], payment["amount"], payment["note"])
                        payment["status"] = "executed"
                        payment["transaction_id"] = result["transaction_id"]
                    except ValueError as error:
                        payment["status"] = "failed"
                        payment["error"] = str(error)
                    results.append(payment.copy())
        session.account = account
        return results

    def change_pin(self, session, old_pin, new_pin):
        if not new_pin.isascii() or not new_pin.isdigit() or len(new_pin) != 4:
            raise ValueError("New PIN must contain four digits")
        with self.repository.transaction() as accounts:
            account = self._fresh(session, accounts)
            if account.card._pin != old_pin:
                raise ValueError("Incorrect current PIN")
            account.card._pin = new_pin
        session.close()

    def block_card(self, session):
        with self.repository.transaction() as accounts:
            account = self._fresh(session, accounts)
            account.card.status = "blocked"
        session.close()

