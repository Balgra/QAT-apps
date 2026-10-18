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
├── docs/class-diagram.drawio      Editable class diagram
└── REQUIREMENTS.md                Behaviour and quality requirements
```

## Run locally

Tkinter is included with standard Windows Python distributions. From `Argentaria`:

```powershell
python app.py
```

Primary demonstration credentials:

- Card: `4556123412341234`
- PIN: `1234`

A second savings account is available as card `4556123412349876`, PIN `4321`.

Transactions modify `data/accounts.json`. Restore the seed file from version control when a class needs a clean starting point.

## Tests

```powershell
python -m pip install -r requirements.txt
python -m pytest
```

Tests work on temporary account files and do not change the supplied accounts.
