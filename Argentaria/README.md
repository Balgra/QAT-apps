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

### Goal of the scenario: Ensure that transaction statements exported from Argentaria can be consistently used across different spreadsheet applications and regional settings.

- **Source:** An authenticated Argentaria customer.
- **Stimulus:** Exports a transaction statement and opens it in spreadsheet software.
- **Artefact:** Backend statement generators and CSV export layer.
- **Environment:** Excel and LibreOffice using the documented English and Swedish CSV import conventions.
- **Response:** Excel and LibreOffice correctly interpret transaction dates, descriptions, EUR amounts and balances correctly, including Swedish characters and punctuation in descriptions.
- **Response measure:** Exported CSV files containing up to 10,000 transactions must not exceed 2 MB.

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
4. Schedule a payment, then select it under **Scheduled payments** and use **Process selected payments** to pay it now, even if its due date is in the future. **Process all due payments** processes only payments due today or earlier.
5. Search transaction history or export an English/Swedish CSV or text statement.
6. Optionally change a PIN or block the active card. Those changes last until the application closes.

Fees are shown before confirmation. See [requirements](REQUIREMENTS.md), [business/statement contracts](docs/contracts.md), and [class diagram](docs/Argentaria.drawio).

## Process scheduled payments

1. Open **Scheduled payments** and select one or more **pending** rows. Use Ctrl/Shift to select multiple rows.
2. Click **Process selected payments**. This processes the selection immediately, including payments dated a year ahead.
3. Review the destinations, amounts, current fees, and total debit. The confirmation explicitly states that future-dated selections will be paid now. Cancel to leave all payments unchanged.
4. Confirm. The system updates sender/recipient balances, records linked transfer entries and any fee, and shows the actual charged fees, total debit, and new balance. The table displays each payment's status, fee, debit, and reference or error.

Use **Process all due payments** for the original date-based behavior: only pending payments due today or earlier in Stockholm are processed, regardless of row selection. Payments are never executed automatically in the background.

Funds including fees and account rules are checked separately for each payment, so some selected payments may succeed while others fail. Failed payments have zero charges. Executed/failed rows cannot be processed again; create a new scheduled payment if you want to retry a failed one. Changed payment details or fees require a new confirmation, and failed storage writes roll back the batch. The activity log includes previews and processing results. All scheduled payments still belong to the current application run.

## Download activity log

Click **Download activity log**, directly below **Eject card** in the sidebar, and choose where to save `argentaria-activity-log.json`. The same button is on the card-entry screen so you can still download the log after ejecting/blocking a card or after an unsuccessful sign-in.

Logging starts automatically when the application opens. It records visited screens, card insertion/ejection, banking service calls, input values, returned results, errors, UTC timestamps, and operation durations. Examples include balance/currency views, fee quotes, deposits, withdrawals, transfers, scheduled payments, history searches, statement generation, PIN changes, and blocking. Calls made while preparing a screen or statement can also appear as separate service entries.

PINs and full card numbers are redacted; session/domain objects are represented by their type rather than private state. Logs describe the current application run across card sign-ins. They contain other demonstration account data and transaction notes, so inspect the file before sharing it.

Downloading creates a JSON snapshot without clearing the log or changing any account. Cancelling the save dialog leaves everything unchanged; file errors are shown in the interface. **Download before closing the application:** the next launch starts a new log. See [activity log format](docs/activity-log.md) for the fields and an example.

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

Install dependencies using the startup instructions or Ubuntu/Debian system packages first. Tests use temporary account files. For a machine without Tkinter/display, add `--ignore=tests/test_ui.py --ignore=tests/test_scheduled_ui.py` to run only backend tests.

Two expected failures describe Swedish CSV compatibility gaps; `--runxfail` exposes them as normal failures. No comparison script or baseline file is required.

## SonarQube

Follow [Setup.md → SonarQube](../Setup.md#sonarqube) to install the local server with Docker on Windows, Linux, or macOS, install `pysonar`, and set `SONAR_TOKEN` in your terminal. One server can analyse both applications. Argentaria does not need to be running for analysis.

When creating the local SonarQube project, use **project key `Arg`** and **display name `QAT Argentaria`**. These match `sonar.projectKey` and `sonar.projectName` in `sonar-project.properties`; keep both unchanged. The key is `Arg`, not `Argentaria`. Use a token authorised for this project.

From **Argentaria**, the directory containing that properties file, run:

```text
pysonar --sonar-host-url=http://localhost:9000
```

The scanner reads the key, name, and analysis paths automatically. Production-source analysis covers startup code in `app.py` plus `domain`, `services`, and `repository`, with `tests` classified separately. The Tkinter UI is outside this analysis. Open **http://localhost:9000**, select **QAT Argentaria**, and inspect **Code** or **Measures → Overall Code**. For the assignment, compare files in `services`.

Static analysis works without running tests. For optional backend coverage, run from **Argentaria**:

```text
python -m pip install --user -r requirements-test.txt
python -B -m pytest tests -p no:cacheprovider --ignore=tests/test_ui.py --ignore=tests/test_scheduled_ui.py --cov=app --cov=domain --cov=services --cov=repository --cov-branch --cov-report=xml:coverage.xml
```

The commands above work in Windows CMD/PowerShell. Use `python3` on Linux/macOS. The test requirements include `pytest-cov`, which supplies the `--cov` options. If using Ubuntu/Debian system packages instead of pip, install coverage support with `sudo apt install python3-pytest-cov python3-coverage` after the startup packages. Other OS-managed Python installations can use an optional environment as described in [Setup.md](../Setup.md).

Then run the scan command from **Argentaria**. The properties file automatically imports `Argentaria/coverage.xml`; no extra coverage flag is needed. SonarQube does not run the tests itself, so regenerate the report after code changes if you want current coverage. Without a report, static analysis still runs but coverage cannot be imported. Keep the server version, project key, and active Python Quality Profile unchanged when comparing scans.
