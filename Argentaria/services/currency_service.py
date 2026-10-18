class CurrencyService:
    def convert(self, euro_amount: float, target_currency: str) -> float:
        if target_currency == "EUR":
            return round(euro_amount, 2)
        if target_currency == "USD":
            return round(euro_amount * 1.1, 2)
        if target_currency == "SEK":
            return round(euro_amount * 9.5, 2)
        raise ValueError("Supported currencies are EUR, USD and SEK")

    def label_for(self, target_currency: str) -> str:
        if target_currency == "EUR":
            return "€"
        if target_currency == "USD":
            return "$"
        if target_currency == "SEK":
            return "kr"
        return target_currency


class ReceiptCurrencyFormatter:
    def amount_in_dollars(self, euro_amount: float) -> str:
        return f"${euro_amount * 1.1:,.2f}"

    def amount_in_krona(self, euro_amount: float) -> str:
        return f"{euro_amount * 9.5:,.2f} kr"

