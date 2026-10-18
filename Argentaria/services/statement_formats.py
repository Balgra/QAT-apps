class SavingsStatement:
    def render_savings(self, details: dict) -> str:
        return f"Savings statement for {details['holder']} — EUR {details['balance_eur']:.2f}"


class CurrentStatement:
    def render_current(self, details: dict) -> str:
        return f"Current statement for {details['holder']} — EUR {details['balance_eur']:.2f}"


class YouthStatement:
    def render_youth(self, details: dict) -> str:
        return f"Youth statement for {details['holder']} — EUR {details['balance_eur']:.2f}"

