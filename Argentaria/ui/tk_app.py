from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from repository import AccountRepository
from services import BankingService, CardSessionGateway, CurrencyService
from services.authentication import CardAuthenticator


INK = "#17211d"
PAPER = "#f3f0e8"
PANEL = "#ffffff"
GREEN = "#164e43"
MINT = "#bce3d2"
GOLD = "#dfb45b"
MUTED = "#69736e"
ERROR = "#a83d2d"


class ArgentariaApp:
    def __init__(self, data_file: Path | None = None):
        self.root = tk.Tk()
        self.root.title("Argentaria Banking")
        self.root.geometry("1120x720")
        self.root.minsize(900, 620)
        self.root.configure(bg=PAPER)
        selected_file = data_file or Path(__file__).resolve().parents[1] / "data" / "accounts.json"
        self.repository = AccountRepository(selected_file)
        self.gateway = CardSessionGateway(CardAuthenticator(self.repository))
        self.banking = BankingService(self.repository, CurrencyService())
        self.session = None
        self.currency = tk.StringVar(value="EUR")
        self.content = None
        self._configure_styles()
        self.show_card_entry()

    def _configure_styles(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("TFrame", background=PAPER)
        style.configure("Panel.TFrame", background=PANEL)
        style.configure("TLabel", background=PAPER, foreground=INK, font=("Segoe UI", 10))
        style.configure("Title.TLabel", background=PAPER, foreground=INK, font=("Georgia", 34, "bold"))
        style.configure("Heading.TLabel", background=PAPER, foreground=INK, font=("Georgia", 19, "bold"))
        style.configure("Muted.TLabel", background=PAPER, foreground=MUTED, font=("Segoe UI", 10))
        style.configure("Panel.TLabel", background=PANEL, foreground=INK, font=("Segoe UI", 10))
        style.configure("PanelMuted.TLabel", background=PANEL, foreground=MUTED, font=("Segoe UI", 9))
        style.configure("Primary.TButton", background=GREEN, foreground="white", padding=(18, 12), borderwidth=0, font=("Segoe UI", 10, "bold"))
        style.map("Primary.TButton", background=[("active", "#0e3f36")])
        style.configure("Secondary.TButton", background="#e4e5dd", foreground=INK, padding=(14, 10), borderwidth=0)
        style.map("Secondary.TButton", background=[("active", "#d7d9d0")])
        style.configure("Side.TButton", background=GREEN, foreground="#d7eee5", padding=(18, 12), borderwidth=0, anchor="w", font=("Segoe UI", 10))
        style.map("Side.TButton", background=[("active", "#0d4036")], foreground=[("active", "white")])
        style.configure("TEntry", fieldbackground="white", bordercolor="#c7ccc6", padding=10)
        style.configure("TCombobox", fieldbackground="white", padding=8)

    def clear(self):
        for child in self.root.winfo_children():
            child.destroy()

    def show_card_entry(self):
        self.clear()
        shell = tk.Frame(self.root, bg=GREEN)
        shell.pack(fill="both", expand=True)
        left = tk.Frame(shell, bg=GREEN, padx=70, pady=55)
        left.pack(side="left", fill="both", expand=True)
        tk.Label(left, text="ARGENTARIA", bg=GREEN, fg="white", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        tk.Label(left, text="Your money,\nclearly in view.", bg=GREEN, fg="white", font=("Georgia", 37, "bold"), justify="left").pack(anchor="w", pady=(100, 18))
        tk.Label(left, text="A simple banking terminal for deposits,\nwithdrawals and account insight.", bg=GREEN, fg="#bce3d2", font=("Segoe UI", 12), justify="left").pack(anchor="w")
        card = tk.Frame(left, bg="#1d6456", width=360, height=190, padx=24, pady=22)
        card.pack(anchor="w", pady=(55, 0)); card.pack_propagate(False)
        tk.Label(card, text="ARGENTARIA  ◈", bg="#1d6456", fg="white", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        tk.Label(card, text="••••  ••••  ••••  1234", bg="#1d6456", fg="white", font=("Consolas", 17)).pack(anchor="w", pady=(52, 7))
        tk.Label(card, text="DENNIS RITCHIE                  12/30", bg="#1d6456", fg="#d4e7e1", font=("Consolas", 9)).pack(anchor="w")

        panel = tk.Frame(shell, bg=PAPER, width=470, padx=64, pady=70)
        panel.pack(side="right", fill="y"); panel.pack_propagate(False)
        tk.Label(panel, text="INSERT CARD", bg=PAPER, fg=MUTED, font=("Segoe UI", 9, "bold")).pack(anchor="w")
        tk.Label(panel, text="Welcome back", bg=PAPER, fg=INK, font=("Georgia", 30, "bold")).pack(anchor="w", pady=(8, 10))
        tk.Label(panel, text="Use the demonstration card to enter the terminal.", bg=PAPER, fg=MUTED, font=("Segoe UI", 10)).pack(anchor="w", pady=(0, 34))
        tk.Label(panel, text="Card number", bg=PAPER, fg=INK, font=("Segoe UI", 9, "bold")).pack(anchor="w")
        card_entry = ttk.Entry(panel, font=("Consolas", 12)); card_entry.insert(0, "4556123412341234"); card_entry.pack(fill="x", pady=(7, 20))
        tk.Label(panel, text="PIN", bg=PAPER, fg=INK, font=("Segoe UI", 9, "bold")).pack(anchor="w")
        pin_entry = ttk.Entry(panel, show="•", font=("Consolas", 12)); pin_entry.insert(0, "1234"); pin_entry.pack(fill="x", pady=(7, 10))
        error_label = tk.Label(panel, text="", bg=PAPER, fg=ERROR, font=("Segoe UI", 9), wraplength=330, justify="left")
        error_label.pack(anchor="w", pady=(0, 12))
        def sign_in():
            try:
                self.session = self.gateway.insert(card_entry.get(), pin_entry.get())
                self.show_dashboard()
            except ValueError as error:
                error_label.config(text=str(error))
        ttk.Button(panel, text="Insert card and continue  →", style="Primary.TButton", command=sign_in).pack(fill="x", pady=(6, 0))
        pin_entry.bind("<Return>", lambda _event: sign_in())
        tk.Label(panel, text="Training data only · no real banking connection", bg=PAPER, fg="#8c958f", font=("Segoe UI", 8)).pack(anchor="center", pady=(25, 0))

    def _dashboard_shell(self, title: str, subtitle: str):
        self.clear()
        sidebar = tk.Frame(self.root, bg=GREEN, width=220, padx=22, pady=28)
        sidebar.pack(side="left", fill="y"); sidebar.pack_propagate(False)
        tk.Label(sidebar, text="ARGENTARIA", bg=GREEN, fg="white", font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0, 45))
        for label, command in [("⌂   Overview", self.show_dashboard), ("＋  Add money", self.show_deposit), ("−   Withdraw", self.show_withdraw), ("◎   Account details", self.show_details)]:
            ttk.Button(sidebar, text=label, style="Side.TButton", command=command).pack(fill="x", pady=2)
        tk.Frame(sidebar, bg="#3b7468", height=1).pack(fill="x", pady=24)
        card = self.session.get_account().card
        tk.Label(sidebar, text=card.customer.full_name, bg=GREEN, fg="white", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        tk.Label(sidebar, text=card.masked_number(), bg=GREEN, fg="#bce3d2", font=("Consolas", 8)).pack(anchor="w", pady=(4, 12))
        ttk.Button(sidebar, text="Eject card", style="Side.TButton", command=self.eject).pack(fill="x")

        body = tk.Frame(self.root, bg=PAPER, padx=46, pady=34)
        body.pack(side="left", fill="both", expand=True)
        head = tk.Frame(body, bg=PAPER); head.pack(fill="x", pady=(0, 30))
        tk.Label(head, text=title, bg=PAPER, fg=INK, font=("Georgia", 28, "bold")).pack(anchor="w")
        tk.Label(head, text=subtitle, bg=PAPER, fg=MUTED, font=("Segoe UI", 10)).pack(anchor="w", pady=(6, 0))
        self.content = tk.Frame(body, bg=PAPER)
        self.content.pack(fill="both", expand=True)

    def show_dashboard(self):
        name = self.session.get_account().card.customer.full_name.split()[0]
        self._dashboard_shell(f"Good day, {name}", "Here is the latest view of your account.")
        balance = self.banking.get_balance(self.session, self.currency.get())
        balance_card = tk.Frame(self.content, bg=GREEN, padx=30, pady=26)
        balance_card.pack(fill="x")
        top = tk.Frame(balance_card, bg=GREEN); top.pack(fill="x")
        tk.Label(top, text="AVAILABLE BALANCE", bg=GREEN, fg="#bce3d2", font=("Segoe UI", 9, "bold")).pack(side="left")
        currency_box = ttk.Combobox(top, textvariable=self.currency, values=["EUR", "USD", "SEK"], state="readonly", width=7)
        currency_box.pack(side="right"); currency_box.bind("<<ComboboxSelected>>", lambda _event: self.show_dashboard())
        tk.Label(balance_card, text=f"{balance['symbol']} {balance['amount']:,.2f}", bg=GREEN, fg="white", font=("Georgia", 38, "bold")).pack(anchor="w", pady=(22, 5))
        tk.Label(balance_card, text="Converted from EUR using the training rate" if self.currency.get() != "EUR" else "Primary account balance", bg=GREEN, fg="#bce3d2", font=("Segoe UI", 9)).pack(anchor="w")
        actions = tk.Frame(self.content, bg=PAPER); actions.pack(fill="x", pady=22)
        for title, note, command, accent in [("Add money", "Deposit funds into this account", self.show_deposit, MINT), ("Withdraw", "Take funds from this account", self.show_withdraw, "#f0d7a6"), ("View details", "Account, card and conversions", self.show_details, "#d9dedb")]:
            item = tk.Frame(actions, bg=PANEL, padx=20, pady=20, highlightbackground="#e1ddd4", highlightthickness=1)
            item.pack(side="left", fill="both", expand=True, padx=(0, 10))
            tk.Frame(item, bg=accent, width=35, height=5).pack(anchor="w", pady=(0, 15))
            tk.Label(item, text=title, bg=PANEL, fg=INK, font=("Georgia", 14, "bold")).pack(anchor="w")
            tk.Label(item, text=note, bg=PANEL, fg=MUTED, font=("Segoe UI", 8), wraplength=170, justify="left").pack(anchor="w", pady=(6, 18))
            ttk.Button(item, text="Open  →", style="Secondary.TButton", command=command).pack(anchor="w")
        details = self.banking.account_details(self.session)
        recent = tk.Frame(self.content, bg=PANEL, padx=22, pady=18, highlightbackground="#e1ddd4", highlightthickness=1)
        recent.pack(fill="both", expand=True)
        tk.Label(recent, text="Recent activity", bg=PANEL, fg=INK, font=("Georgia", 15, "bold")).pack(anchor="w", pady=(0, 10))
        if not details["transactions"]:
            tk.Label(recent, text="No transactions yet.", bg=PANEL, fg=MUTED).pack(anchor="w")
        for item in details["transactions"][:4]:
            row = tk.Frame(recent, bg=PANEL, pady=8); row.pack(fill="x")
            sign = "+" if item["kind"] == "DEPOSIT" else "−"
            tk.Label(row, text=item["kind"].title(), bg=PANEL, fg=INK, font=("Segoe UI", 9, "bold")).pack(side="left")
            tk.Label(row, text=f"{sign} €{item['amount']:,.2f}", bg=PANEL, fg=GREEN if sign == "+" else INK, font=("Segoe UI", 9, "bold")).pack(side="right")

    def _show_money_form(self, operation: str):
        is_deposit = operation == "deposit"
        self._dashboard_shell("Add money" if is_deposit else "Withdraw money", "Enter an amount in euros. The training account updates immediately.")
        form = tk.Frame(self.content, bg=PANEL, padx=34, pady=30, highlightbackground="#e1ddd4", highlightthickness=1)
        form.pack(fill="x")
        tk.Label(form, text="AMOUNT (EUR)", bg=PANEL, fg=MUTED, font=("Segoe UI", 9, "bold")).pack(anchor="w")
        amount = ttk.Entry(form, font=("Georgia", 24)); amount.pack(fill="x", pady=(9, 24)); amount.focus_set()
        tk.Label(form, text="NOTE (OPTIONAL)", bg=PANEL, fg=MUTED, font=("Segoe UI", 9, "bold")).pack(anchor="w")
        note = ttk.Entry(form); note.pack(fill="x", pady=(9, 12))
        feedback = tk.Label(form, text="", bg=PANEL, fg=ERROR, font=("Segoe UI", 9)); feedback.pack(anchor="w", pady=(0, 10))
        def submit():
            try:
                value = float(amount.get())
                result = self.banking.deposit(self.session, value, note.get()) if is_deposit else self.banking.withdraw(self.session, value, note.get())
                messagebox.showinfo("Transaction complete", f"Reference {result['transaction_id']}\nNew balance: €{result['balance']:,.2f}")
                self.show_dashboard()
            except ValueError as error:
                feedback.config(text=str(error))
        ttk.Button(form, text=("Confirm deposit  →" if is_deposit else "Confirm withdrawal  →"), style="Primary.TButton", command=submit).pack(anchor="w", pady=(8, 0))
        amount.bind("<Return>", lambda _event: submit())

    def show_deposit(self):
        self._show_money_form("deposit")

    def show_withdraw(self):
        self._show_money_form("withdraw")

    def show_details(self):
        self._dashboard_shell("Account details", "Your identity, account references and converted balances.")
        details = self.banking.account_details(self.session)
        grid = tk.Frame(self.content, bg=PAPER); grid.pack(fill="both", expand=True)
        identity = tk.Frame(grid, bg=PANEL, padx=24, pady=22, highlightbackground="#e1ddd4", highlightthickness=1)
        identity.pack(side="left", fill="both", expand=True, padx=(0, 10))
        account = tk.Frame(grid, bg=PANEL, padx=24, pady=22, highlightbackground="#e1ddd4", highlightthickness=1)
        account.pack(side="left", fill="both", expand=True)
        tk.Label(identity, text="Account holder", bg=PANEL, fg=INK, font=("Georgia", 16, "bold")).pack(anchor="w", pady=(0, 18))
        for label, value in [("NAME", details["holder"]), ("EMAIL", details["email"]), ("PHONE", details["phone"]), ("ADDRESS", details["address"])]:
            tk.Label(identity, text=label, bg=PANEL, fg=MUTED, font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(8, 2))
            tk.Label(identity, text=value, bg=PANEL, fg=INK, font=("Segoe UI", 9), wraplength=290, justify="left").pack(anchor="w")
        tk.Label(account, text="Banking details", bg=PANEL, fg=INK, font=("Georgia", 16, "bold")).pack(anchor="w", pady=(0, 18))
        for label, value in [("ACCOUNT", details["account_number"]), ("IBAN", details["iban"]), ("TYPE", details["account_type"]), ("CARD", details["card"]), ("FEATURE", details["account_feature"])]:
            tk.Label(account, text=label, bg=PANEL, fg=MUTED, font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(8, 2))
            tk.Label(account, text=value, bg=PANEL, fg=INK, font=("Segoe UI", 9), wraplength=290, justify="left").pack(anchor="w")
        conversions = tk.Frame(self.content, bg=GREEN, padx=24, pady=18)
        conversions.pack(fill="x", pady=(12, 0))
        tk.Label(conversions, text=f"€ {details['balance_eur']:,.2f}", bg=GREEN, fg="white", font=("Georgia", 16, "bold")).pack(side="left")
        tk.Label(conversions, text=f"$ {details['balance_usd']:,.2f}", bg=GREEN, fg=MINT, font=("Georgia", 16, "bold")).pack(side="left", padx=50)
        tk.Label(conversions, text=f"{details['balance_sek']:,.2f} kr", bg=GREEN, fg="#f0d7a6", font=("Georgia", 16, "bold")).pack(side="left")

    def eject(self):
        if self.session:
            self.session.close()
        self.session = None
        self.currency.set("EUR")
        self.show_card_entry()

    def run(self):
        self.root.mainloop()

