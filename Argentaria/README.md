# Argentaria

Argentaria is a small desktop banking terminal built with Python and Tkinter. A customer inserts a demonstration card, enters a PIN, views account information, deposits or withdraws euros, reviews recent activity, and sees the balance converted to US dollars or Swedish kronor.

## Project map

```text
Argentaria/
├── app.py                         Application entry point
├── ui/tk_app.py                   Tkinter interface
├── domain/                        Account, card, customer and transaction objects
├── services/                      Authentication, banking, currency and cash operations
├── repository/account_repository.py
│                                  JSON persistence
├── data/accounts.json             Mock accounts
├── tests/                         Backend behaviour tests
├── docs/Argentaria.drawio         Editable class diagram
├── docs/contracts.md              Fees, limits and statement import conventions
└── REQUIREMENTS.md                Behaviour and quality requirements
```

## Compatibility quality scenario

- **Source:** An authenticated Argentaria customer.
- **Stimulus:** Exports a transaction statement and opens it in spreadsheet software.
- **Artefact:** Backend statement generators and CSV export layer.
- **Environment:** Excel and LibreOffice using the documented English and Swedish CSV import conventions.
- **Response:** Both applications interpret transaction dates, descriptions, EUR amounts, and balances correctly, including Swedish characters and punctuation in descriptions.
- **Response measure:** Target: 100% of fixture rows preserve field values and imported numeric totals match Argentaria's statement totals exactly, with zero split or missing records.

This is an acceptance target, not an achieved measurement. See `docs/contracts.md` for the import conventions and reproducible compatibility checks.

## Run locally

Install Python **3.10+** with Tkinter. See [Setup.md](../Setup.md) for OS installation options, including Ubuntu/Debian system packages. No shared Python environment is required.

From **QAT-apps**, use the commands for your terminal.

**Windows CMD or PowerShell:**

```text
cd Argentaria
python -m pip install --user -r requirements.txt
python -B app.py
```

If Windows uses `py` instead of `python`, use `py` for both commands.

**Linux/macOS with a Python installation that permits pip installs:**

```bash
cd Argentaria
python3 -m pip install --user -r requirements.txt
python3 -B app.py
```

Ubuntu/Debian users can use the short system-package procedure in [Setup.md](../Setup.md#argentaria) instead of pip. Tkinter needs a graphical desktop; `python -m tkinter` (or `python3 -m tkinter`) checks that it can open a window.

Close the application window to stop it. Every launch uses a temporary copy of the supplied `data/accounts.json`, so the same accounts, balances, cards, and PINs are available again. Re-inserting a card during the same application run keeps that run's changes.

## Demo accounts and actions

| Account | Card | PIN |
| --- | --- | --- |
| Current | `4556123412341234` | `1234` |
| Savings | `4556123412349876` | `4321` |
| Premium | `4556123412345555` | `5555` |

1. Insert a demonstration card and enter its PIN.
2. View the balance/details, deposit or withdraw euros, or convert the displayed balance to USD/SEK.
3. Transfer to another account number shown under **Account details**; the Savings destination is `1000 2200 7788`.
4. Schedule a payment, then use **Process due payments** when you want to execute due payments.
5. Search transaction history or export an English/Swedish CSV or text statement.
6. Optionally change a PIN or block the active card. Those changes last until the application closes.

Fees are shown before confirmation. See [requirements](REQUIREMENTS.md), [business/statement contracts](docs/contracts.md), and [class diagram](docs/Argentaria.drawio).

## Tests

From **Argentaria**, run the supplied tests directly.

**Windows CMD or PowerShell:**

```text
python -m pip install --user -r requirements.txt
python -B -m pytest tests -p no:cacheprovider
```

**Linux/macOS:**

```bash
python3 -B -m pytest tests -p no:cacheprovider
```

Install dependencies using the startup instructions or Ubuntu/Debian system packages first. Tests use temporary account files. For a machine without Tkinter/display, add `--ignore=tests/test_ui.py` to run only backend tests.

Two expected failures describe Swedish CSV compatibility gaps; `--runxfail` exposes them as normal failures. No comparison script or baseline file is required.

## SonarQube (optional)

With `pysonar` installed, your server running, and `SONAR_TOKEN` set locally, scan from **Argentaria**:

```text
pysonar --sonar-host-url=http://localhost:9000 --sonar-project-key=Arg
```

The scan covers startup code in `app.py` plus `domain`, `services`, and `repository`. For optional coverage, run from **Argentaria**:

```text
python -m pip install --user -r requirements-test.txt
python -B -m pytest tests -p no:cacheprovider --ignore=tests/test_ui.py --cov=app --cov=domain --cov=services --cov=repository --cov-branch --cov-report=xml:coverage.xml
```

Use `python3` on Linux/macOS. Then run the scan command from **Argentaria**. The properties file automatically imports `coverage.xml`; no extra coverage flag is needed. Without a report, static analysis still runs but coverage cannot be imported. The active SonarQube Quality Profile controls which rules are checked; keep it and the project key unchanged when comparing scans.
