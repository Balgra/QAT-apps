# Refit

Refit is a small circular-fashion marketplace. Shoppers browse twenty pre-loved garments, search and filter the catalog, build a cart, enter delivery and demonstration-card details, and place an order. FastAPI supplies product CRUD and checkout operations, while a JSON file stands in for a database.

## Project map

```text
Refit/
├── docker-compose.yml        Starts the complete application
├── frontend/                 React + Vite client
│   ├── Dockerfile            Builds React and serves it with Nginx
│   ├── nginx.conf            SPA routing and /api reverse proxy
│   ├── src/App.jsx           Storefront, cart, checkout and confirmation
│   ├── src/Operations.jsx    Order controls and seller studio
│   └── src/api.js            Shared browser API client
├── backend/
│   ├── Dockerfile            Runs the FastAPI service
│   ├── app/main.py           FastAPI routes and application factory
│   ├── app/checkout.py       Checkout orchestration
│   ├── app/commerce.py       Orders, returns, reservations and seller operations
│   ├── app/storage.py        Atomic JSON state transactions
│   ├── app/pricing.py        Pricing and discount policy
│   ├── app/repository.py     JSON catalog persistence
│   ├── data/products.json    Mock database with 20 garments
│   └── tests/                API behaviour tests
├── docs/Refit.drawio         Editable frontend/backend architecture map
├── docs/contracts.md         Business policies and client compatibility contracts
└── REQUIREMENTS.md           Behaviour and quality requirements
```

## Compatibility quality scenario

- **Source:** Refit React storefront or a supported API client.
- **Stimulus:** Submits cart and delivery information for a quote or checkout.
- **Artefact:** FastAPI request handling, checkout service, and pricing layer.
- **Environment:** Current v2 storefront and the documented previous v1 client exchange checkout payloads with the same backend.
- **Response:** Correctly interprets product identifiers, quantities, delivery options, and coupons and returns a price breakdown each client can use.
- **Response measure:** Target: 100% of valid cases in the versioned compatibility suite produce the expected order and totals, with zero failures due to supported payload differences.

This is an acceptance target, not an achieved measurement. See `docs/contracts.md` for client fixtures and reproducible compatibility checks.

## Run locally

### Docker (recommended)

Works in Windows CMD, PowerShell, Linux Bash, and macOS Zsh. Install and start Docker with Compose, then run from **QAT-apps**.

Docker builds separate backend and frontend images with their dependencies included.
Compose connects the containers, and Nginx forwards the storefront's API calls to FastAPI.
Every new backend process starts with a temporary copy of the supplied catalog.

```text
cd Refit
docker compose up -d --build --force-recreate
```

Open **http://localhost:5173**; API documentation is at **http://localhost:8000/docs**. The command recreates the containers to start a fresh run, even if an older run is still active. After editing code, run the same command to rebuild it. Stop the app from `Refit` with `docker compose down`.

### Without Docker

Install Python **3.10+** and Node.js 22/npm. Open two terminals in **QAT-apps**.

**Backend — Windows CMD or PowerShell:**

```text
cd Refit/backend
python -m pip install --user -r requirements.txt
python -B -m uvicorn app.main:app --reload
```

**Backend — Linux/macOS:**

```bash
cd Refit/backend
python3 -m pip install --user -r requirements.txt
python3 -B -m uvicorn app.main:app --reload
```

If your OS blocks direct pip installs, use the Docker option or your own optional Python environment. See [Setup.md](../Setup.md).

**Frontend — Windows CMD or PowerShell, in the second terminal:**

```text
cd Refit/frontend
npm.cmd ci
npm.cmd run dev
```

**Frontend — Linux/macOS, in the second terminal:**

```bash
cd Refit/frontend
npm ci
npm run dev
```

Keep both terminals open. Stop each native server with **Ctrl+C**. A backend restart, including a development reload after editing Python code, begins a fresh run. Refreshing the browser does not restart the backend.

## Using the shop

The catalog has **20 listings from five sellers**: Mira, Linnea, Noah, Elias, and Ava, with four listings per seller and varied quantities.

1. Add clothes to the bag and proceed to checkout.
2. Enter valid delivery details. Use demonstration card `4242 4242 4242 4242`, a future `MM/YY`, and a three-digit CVV.
3. Optionally review the final total, use coupon `WELCOME10`, or hold the cart for ten minutes. Keep the same email for a hold.
4. Buy the items and open **Orders / seller studio**.
5. Choose an order reference and click **Find order** to view it. The saved order's first seller loads automatically.
6. View sales and pending earnings. Mark an order dispatched and then delivered to move its earnings to the available payout estimate. Refunds and cancellations reduce the amounts.

The Gold demo profile is `member@refit.example`. Seller, listing-review, and fulfilment controls are demonstration controls without separate accounts. Earnings are estimates, not actual bank transfers.

The supplied `backend/data/products.json` is unchanged by normal use. Changes are saved to a temporary JSON file for the current backend run, so everyone starts with the same products and empty order history on the next launch.

See [requirements](REQUIREMENTS.md), [business/API contracts](docs/contracts.md), and [architecture](docs/Refit.drawio).

## Tests

From **Refit/backend**, run the provided tests directly. On Windows:

```text
python -m pip install --user -r requirements.txt
python -B -m pytest tests -p no:cacheprovider
```

On Linux/macOS, use `python3` instead of `python`. Alternatively, after building the Docker images, run from **Refit** in any shell:

```text
docker compose run --rm backend python -B -m pytest tests -p no:cacheprovider
```

Tests use temporary files. Two expected failures describe the previous-client compatibility gaps; `--runxfail` exposes them as normal failures. No baseline file or comparison script is needed.

For frontend tests, run `npm.cmd test` on Windows or `npm test` on Linux/macOS from `Refit/frontend`, after installing npm dependencies.

## SonarQube (optional)

With `pysonar` installed, your server running, and `SONAR_TOKEN` set locally, scan from **Refit**:

```text
pysonar --sonar-host-url=http://localhost:9000 --sonar-project-key=Refit
```

Only `backend/app` is analysed. For coverage, first run from **Refit/backend**:

```text
python -m pip install --user -r requirements-test.txt
python -B -m pytest tests -p no:cacheprovider --cov=app --cov-branch --cov-report=xml:../coverage.xml
```

Use `python3` on Linux/macOS. Then run the scan command from **Refit**. The properties file automatically imports `coverage.xml`; no extra coverage flag is needed. SonarQube does not run the tests itself, so generate a fresh report after code changes if you want current coverage. Without a report, static analysis still runs but coverage cannot be imported. The active SonarQube Quality Profile controls which rules are checked.

