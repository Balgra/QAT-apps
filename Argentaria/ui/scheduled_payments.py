"""Selection, cost confirmation, and results for scheduled transfers."""
from tkinter import messagebox, ttk

from services.activity_log import ActivityLog
from services.authentication import CardSession
from services.banking_service import BankingService


class ScheduledPaymentsView(ttk.Frame):
    def __init__(self, master, banking: BankingService, session: CardSession, activity_log: ActivityLog):
        super().__init__(master)
        self.banking = banking
        self.session = session
        self.activity_log = activity_log
        self._payments = {}
        columns = ("date", "destination", "amount", "fee", "total", "status", "result")
        self.table = ttk.Treeview(self, columns=columns, show="headings", selectmode="extended", height=10)
        for name, title, width in zip(columns, ("Due date", "Destination", "Amount EUR", "Fee EUR", "Debited EUR", "Status", "Reference / error"),
                                      (110, 140, 95, 85, 100, 100, 240)):
            self.table.heading(name, text=title)
            self.table.column(name, width=width, minwidth=70)
        vertical = ttk.Scrollbar(self, orient="vertical", command=self.table.yview)
        horizontal = ttk.Scrollbar(self, orient="horizontal", command=self.table.xview)
        self.table.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        self.table.grid(row=0, column=0, sticky="nsew")
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        ttk.Label(self, text="Select pending payments to pay now, including future dates. Use Ctrl/Shift for multiple rows.",
                  wraplength=570).grid(row=2, column=0, sticky="w", pady=(12, 4))
        actions = ttk.Frame(self)
        actions.grid(row=3, column=0, sticky="w", pady=10)
        self.selected_button = ttk.Button(actions, text="Process selected payments", command=lambda: self.process(True))
        self.selected_button.pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Process all due payments", command=lambda: self.process(False)).pack(side="left")
        self.table.bind("<<TreeviewSelect>>", lambda _event: self._update_selection())
        self.refresh()

    def refresh(self) -> None:
        payments = self.banking.scheduled_payments(self.session)
        self._payments = {payment["id"]: payment for payment in payments}
        self.table.delete(*self.table.get_children())
        for payment in payments:
            fee = f"{payment['fee']:.2f}" if "fee" in payment else "—"
            total = f"{payment['total_debited']:.2f}" if "total_debited" in payment else "—"
            status = "pending" if payment["status"] == "due" else payment["status"]
            self.table.insert("", "end", iid=payment["id"], values=(
                payment["due_date"], payment["destination"], f"{payment['amount']:.2f}", fee, total, status,
                payment.get("error", payment.get("transaction_id", "")),
            ))
        self._update_selection()

    def _selected_ids(self) -> list[str]:
        selected = set(self.table.selection())
        return [key for key in self.table.get_children() if key in selected]

    def _update_selection(self) -> None:
        selected = self._selected_ids()
        pending = selected and all(self._payments[key]["status"] == "due" for key in selected)
        self.selected_button.configure(state="normal" if pending else "disabled")

    def process(self, selected_only: bool) -> None:
        references = self._selected_ids() if selected_only else None
        try:
            quote = self.banking.preview_scheduled_payments(self.session, references)
            if not quote["payments"]:
                messagebox.showinfo("Scheduled payments", "No pending payments are due yet.", parent=self)
                return
            if not self._confirm(quote, selected_only):
                self.activity_log.record("confirmation.cancel", {"operation": "scheduled payments", "payment_ids": references})
                return
            results = self._execute(references, quote["payments"])
            self.refresh()
            self._show_results(results)
        except (ValueError, OSError) as error:
            messagebox.showerror("Scheduled payments", str(error), parent=self)

    def _confirm(self, quote: dict, selected_only: bool) -> bool:
        details = [f"{payment['destination']} · scheduled {payment['due_date']}\n"
                   f"Amount EUR {payment['amount']:.2f} + fee EUR {payment['fee']:.2f}"
                   for payment in quote["payments"]]
        timing = "Selected future-dated payments will be paid immediately." if selected_only else "Only payments due today or earlier will be paid."
        totals = (f"\n\nTotal amount: EUR {quote['amount']:.2f}\nTotal fees: EUR {quote['fee']:.2f}"
                  f"\nTotal debit if all succeed: EUR {quote['total_debited']:.2f}"
                  f"\nCurrent balance: EUR {quote['balance']:.2f}"
                  f"\n\n{timing}\nFunds and account rules are checked for each payment. Continue?")
        return messagebox.askyesno("Confirm scheduled payments", "\n\n".join(details) + totals, parent=self)

    def _execute(self, references: list[str] | None, expected: list[dict]) -> list[dict]:
        if references is None:
            return self.banking.process_due_payments(self.session, expected_payments=expected)
        return self.banking.process_scheduled_payments(self.session, references, expected_payments=expected)

    def _show_results(self, results: list[dict]) -> None:
        succeeded = [payment for payment in results if payment["status"] == "executed"]
        fees = sum(payment["fee"] for payment in succeeded)
        debited = sum(payment["total_debited"] for payment in succeeded)
        balance = self.banking.get_balance(self.session)["amount"]
        messagebox.showinfo("Payments processed", (
            f"Executed: {len(succeeded)} · Failed: {len(results) - len(succeeded)}"
            f"\nFees charged: EUR {fees:.2f}\nTotal debited: EUR {debited:.2f}"
            f"\nNew balance: EUR {balance:.2f}"
            "\nSee each row for its transaction reference or error."
        ), parent=self)
