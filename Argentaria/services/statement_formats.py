import csv
import io
from datetime import datetime
from zoneinfo import ZoneInfo


class AccountStatement:
    def csv(self, details, locale):
        raise NotImplementedError

    def text(self, details):
        lines = [details["account_type"] + " statement", details["holder"], details["iban"],
                 f"Balance EUR {details['balance_eur']:.2f}",
                 f"Balance USD {details['balance_eur'] * 1.1:.2f}",
                 f"Balance SEK {details['balance_eur'] * 9.5:.2f}"]
        for item in details["transactions"]:
            lines.append(f"{item['timestamp']} {item['kind']} {item['amount']:.2f} {item['note']}")
        return "\n".join(lines)


class SavingsStatement(AccountStatement):
    def render_savings(self, details):
        return self.text(details)

    def csv(self, details, locale):
        output = io.StringIO(newline="")
        delimiter = ";" if locale == "sv" else ","
        writer = csv.writer(output, delimiter=delimiter, lineterminator="\r\n")
        writer.writerow(["Date", "Reference", "Type", "Description", "Amount EUR", "Balance EUR"])
        for item in details["transactions"]:
            amount = item["amount"]
            if item["kind"] in {"WITHDRAWAL", "TRANSFER_OUT", "FEE"}:
                amount = -amount
            moment = datetime.fromisoformat(item["timestamp"])
            if moment.tzinfo:
                moment = moment.astimezone(ZoneInfo("Europe/Stockholm"))
            date_text = moment.date().isoformat()
            reference = item["transaction_id"]
            kind = item["kind"]
            description = item["note"]
            amount_text = f"{amount:.2f}"
            balance_text = f"{item['balance_after']:.2f}"
            if locale == "sv":
                date_text = date_text.replace("-", "/")
            writer.writerow([date_text, reference, kind, description, amount_text, balance_text])
        return output.getvalue()


class CurrentStatement(AccountStatement):
    def render_current(self, details):
        return self.text(details)

    def csv(self, details, locale):
        output = io.StringIO(newline="")
        delimiter = ";" if locale == "sv" else ","
        writer = csv.writer(output, delimiter=delimiter, lineterminator="\r\n")
        writer.writerow(["Date", "Reference", "Type", "Description", "Amount EUR", "Balance EUR"])
        for item in details["transactions"]:
            amount = item["amount"]
            if item["kind"] in {"WITHDRAWAL", "TRANSFER_OUT", "FEE"}:
                amount = -amount
            moment = datetime.fromisoformat(item["timestamp"])
            if moment.tzinfo:
                moment = moment.astimezone(ZoneInfo("Europe/Stockholm"))
            date_text = moment.date().isoformat()
            reference = item["transaction_id"]
            kind = item["kind"]
            description = item["note"]
            amount_text = f"{amount:.2f}"
            balance_text = f"{item['balance_after']:.2f}"
            if locale == "sv":
                date_text = date_text.replace("-", "/")
            writer.writerow([date_text, reference, kind, description, amount_text, balance_text])
        return output.getvalue()


class PremiumStatement(CurrentStatement):
    def csv(self, details, locale):
        output = io.StringIO(newline="")
        delimiter = ";" if locale == "sv" else ","
        writer = csv.writer(output, delimiter=delimiter, lineterminator="\r\n")
        writer.writerow(["Date", "Reference", "Type", "Description", "Amount EUR", "Balance EUR"])
        for item in details["transactions"]:
            amount = item["amount"]
            if item["kind"] in {"WITHDRAWAL", "TRANSFER_OUT", "FEE"}:
                amount = -amount
            moment = datetime.fromisoformat(item["timestamp"])
            if moment.tzinfo:
                moment = moment.astimezone(ZoneInfo("Europe/Stockholm"))
            date_text = moment.date().isoformat()
            reference = item["transaction_id"]
            kind = item["kind"]
            description = item["note"]
            amount_text = f"{amount:.2f}"
            balance_text = f"{item['balance_after']:.2f}"
            if locale == "sv":
                date_text = date_text.replace("-", "/")
            writer.writerow([date_text, reference, kind, description, amount_text, balance_text])
        return output.getvalue()

