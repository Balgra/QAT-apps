# Refit

Refit is a small circular-fashion marketplace. Shoppers browse twenty pre-loved garments, search and filter the catalog, build a cart, enter delivery and demonstration-card details, and place an order. FastAPI supplies product CRUD and checkout operations, while a JSON file stands in for a database.

## Project map

```text
Refit/
├── docker-compose.yml        Starts the complete application
├── frontend/                 React + Vite client
│   ├── Dockerfile            Builds React and serves it with Nginx
│   ├── nginx.conf            SPA routing and /api reverse proxy
│   └── src/App.jsx           Storefront, cart, checkout and confirmation
├── backend/
│   ├── Dockerfile            Runs the FastAPI service
│   ├── app/main.py           FastAPI routes and application factory
│   ├── app/checkout.py       Checkout orchestration
│   ├── app/pricing.py        Pricing and discount policy
│   ├── app/repository.py     JSON catalog persistence
│   ├── data/products.json    Mock database with 20 garments
│   └── tests/                API behaviour tests
├── docs/architecture.drawio  Editable frontend/backend architecture map
└── REQUIREMENTS.md           Behaviour and quality requirements
```

## Run locally

### Recommended: Docker

Students only need Docker Desktop or another Docker Compose installation. From the `Refit` directory, run:

```powershell
docker compose up --build
```

Then open `http://localhost:5173`. The FastAPI documentation remains available at `http://localhost:8000/docs`.

The Compose configuration builds the React application, serves it through Nginx, starts FastAPI, waits for the backend health check, and proxies browser requests from `/api` to the backend. Catalog changes are persisted in `backend/data/products.json` on the host.

Stop the application with:

```powershell
docker compose down
```

### Without Docker

Open two terminals from `Refit`.

Backend (PowerShell):

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

Frontend:

```powershell
cd frontend
npm install
npm run dev
```

Visit `http://localhost:5173`. The API documentation is available at `http://localhost:8000/docs`.

Use demonstration card `4242 4242 4242 4242`, any future `MM/YY`, and any three-digit CVV. `WELCOME10` is an example coupon.

## Tests

From `Refit/backend`, with its dependencies installed:

```powershell
python -m pytest
```

