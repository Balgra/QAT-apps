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

### Goal of the scenario: Ensure that checkout requests from different client versions can be consistently processed by the same backend service.

- **Source:** Refit React storefront.
- **Stimulus:** Submits cart and delivery information for a checkout.
- **Artefact:** FastAPI request handling, checkout service and pricing layer.
- **Environment:** The storefront communicates with the running FastAPI backend.
- **Response:** The backend correctly interprets product identifiers, quantities, delivery options, coupons and returns a price breakdown each client can use.
- **Response measure:** Target: 95% of checkout requests from supported clients receive a complete price breakdown within 500 ms.

This is an acceptance target, not an achieved measurement. See `docs/contracts.md` for client fixtures and reproducible compatibility checks.

## Run locally

### Docker (recommended)

Works in Windows CMD, PowerShell, Linux Bash, and macOS Zsh. [Install Docker](https://docs.docker.com/get-started/get-docker/) with Compose and start it, then run from **QAT-apps**.

Docker builds separate backend and frontend images with their dependencies included.
Compose connects the containers, and Nginx forwards the storefront's API calls to FastAPI.
Every new backend process starts with a temporary copy of the supplied catalog.

```text
cd Refit
docker compose up -d --build --force-recreate
```

Open **http://localhost:5173**; API documentation is at **http://localhost:8000/docs**. The command recreates the containers to start a fresh run, even if an older run is still active. After editing code, run the same command to rebuild it. Stop the app from `Refit` with `docker compose down`.

### Without Docker

Install Python **3.10+** and Node.js **22.12 or newer in the Node 22 release line**, with npm. Open two terminals in **QAT-apps**.

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

Keep both terminals open. Open the frontend URL printed by Vite (normally **http://localhost:5173**); API documentation is at **http://localhost:8000/docs**. Stop each native server with **Ctrl+C**. A backend restart, including a development reload after editing Python code, begins a fresh run. Refreshing the browser does not restart the backend.

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

## Download activity log

To download the API calls made during the current backend run, open **http://localhost:8000/api/activity-log** in your browser. It downloads `refit-activity-log.json`. With Docker, **http://localhost:5173/api/activity-log** accesses the same endpoint through the frontend proxy. This feature is API-only; there is no storefront logging button.

The file contains each completed API call's HTTP method, path, query parameters, incoming JSON payload, outgoing JSON payload, status code, UTC timestamp, and duration. This includes rejected/failed calls and automatic health checks. Logging is automatic: use the shop first, then download the file for your report or debugging.

Card details, credential fields, and validation-error input values are redacted. Request/response headers are not collected. Non-JSON, incomplete, or larger-than-1-MiB bodies are represented by capture metadata rather than raw contents. Downloading the log does not record the log inside itself or clear existing entries. Frontend-only actions that send no API request cannot appear in this backend log.

**Download before stopping or restarting the backend:** each new run starts a new log. The log covers the local backend run, not an individual browser account. See [activity log format](docs/activity-log.md) for field definitions and an example.

**Windows PowerShell:**

```powershell
Invoke-WebRequest -Uri http://localhost:8000/api/activity-log -OutFile refit-activity-log.json
```

**Windows CMD:**

```bat
curl.exe --fail http://localhost:8000/api/activity-log --output refit-activity-log.json
```

**Linux/macOS:**

```bash
curl --fail http://localhost:8000/api/activity-log --output refit-activity-log.json
```

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

## SonarQube

Follow [Setup.md → SonarQube](../Setup.md#sonarqube) to install the local server with Docker on Windows, Linux, or macOS, install `pysonar`, and set `SONAR_TOKEN` in your terminal. One server can analyse both applications. Refit does not need to be running for analysis.

When creating the local SonarQube project, use **project key `Refit`** and **display name `QAT Refit`**. These match `sonar.projectKey` and `sonar.projectName` in `sonar-project.properties`; keep both unchanged. Use a token authorised for this project.

From **Refit**, the directory containing that properties file, run:

```text
pysonar --sonar-host-url=http://localhost:9000
```

The scanner reads the key, name, and analysis paths automatically. Production-source analysis covers `backend/app`, with `backend/tests` classified as tests. The React frontend is outside this analysis. Open **http://localhost:9000**, select **QAT Refit**, and inspect **Code** or **Measures → Overall Code**. For the assignment, compare files in `backend/app`.

Static analysis works without running tests. To include coverage, first run from **Refit/backend** with locally installed Python/dependencies, even if the application itself runs in Docker:

```text
python -m pip install --user -r requirements-test.txt
python -B -m pytest tests -p no:cacheprovider --cov=app --cov-branch --cov-report=xml:../coverage.xml
```

The commands above work in Windows CMD/PowerShell. Use `python3` on Linux/macOS; if the OS blocks pip, see [Setup.md](../Setup.md) for the optional-environment alternative. The test requirements include `pytest-cov`, which supplies the `--cov` options.

Return to **Refit** with `cd ..`, then run the scan command. The properties file automatically imports `Refit/coverage.xml`; no extra coverage flag is needed. SonarQube does not run the tests itself, so generate a fresh report after code changes if you want current coverage. Without a report, static analysis still runs but coverage cannot be imported. Keep the server version, project key, and active Python Quality Profile unchanged when comparing scans.

