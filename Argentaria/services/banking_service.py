from __future__ import annotations

from datetime import datetime

from repository import AccountRepository
from .currency_service import CurrencyService
from .transaction_processors import CashDepositProcessor, CashWithdrawalProcessor


class AuditRelay:
    def write(self, account, action: str) -> None:
        account._last_audit_message = f"{datetime.now().isoformat(timespec='seconds')}:{action}"


class BankingService:
    def __init__(self, repository: AccountRepository, currency_service: CurrencyService):
        self.repository = repository
        self.currency_service = currency_service
        self.deposit_processor = CashDepositProcessor()
        self.withdrawal_processor = CashWithdrawalProcessor()
        self.audit_relay = AuditRelay()
        self.terminal_id = "GOT-ATM-04"
        self.location = "Gothenburg Central"
        self.operator = "SELF-SERVICE"

    def get_balance(self, session, display_currency: str = "EUR") -> dict:
        if session is None or not session.active:
            raise ValueError("Insert a card first")
        account = session.get_account()
        euro = account.get_balance()
        converted = self.currency_service.convert(euro, display_currency)
        self.audit_relay.write(account, "BALANCE_VIEW")
        return {"amount": converted, "currency": display_currency, "symbol": self.currency_service.label_for(display_currency), "base_amount": euro}

    def deposit(self, session, amount: float, note: str = "") -> dict:
        if session is None or not session.active:
            raise ValueError("Insert a card first")
        account = session.get_account()
        transaction = self.deposit_processor.process(account, amount, self.repository, self.location, self.terminal_id, self.operator, "CASH-IN", note, "EUR", True)
        self.audit_relay.write(account, "DEPOSIT")
        return {"transaction_id": transaction.transaction_id, "amount": transaction.amount, "balance": account.get_balance(), "kind": transaction.kind}

    def withdraw(self, session, amount: float, note: str = "") -> dict:
        if session is None or not session.active:
            raise ValueError("Insert a card first")
        account = session.get_account()
        transaction = self.withdrawal_processor.process(account, amount, self.repository, self.location, self.terminal_id, self.operator, "CASH-OUT", note, "EUR", True)
        self.audit_relay.write(account, "WITHDRAWAL")
        return {"transaction_id": transaction.transaction_id, "amount": transaction.amount, "balance": account.get_balance(), "kind": transaction.kind}

    def account_details(self, session) -> dict:
        if session is None or not session.active:
            raise ValueError("Insert a card first")
        account = session.get_account()
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
        elif account.account_type == "Current":
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

