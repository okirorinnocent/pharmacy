# MedSupply Uganda 💊

A B2B pharmaceutical wholesale marketplace for Uganda. Drug shops and pharmacies browse stock, place orders, pay by mobile money or trade credit and track deliveries, while wholesaler staff manage inventory, outlets, credit lines and dispatch from one place.

The repository has two parts:

| Part | What it is | Status |
|---|---|---|
| **Streamlit web app** (`streamlit_app.py`, `forecast.py`) | The full marketplace and admin console | Working, deployable |
| **FastAPI + WhatsApp backend** (`app/`) | WhatsApp ordering bot, MTN MoMo collections and a micro-credit engine on Supabase | Prototype, not yet connected to the web app |

---

## Features

### Web app (Streamlit)

- **Marketplace and cart**: category browsing (Antibiotics, Analgesics, Antimalarial, Medical Consumables, Fluids & Nutrition), favourites, bulk discounts (5% from 10 units, 10% from 50) and reorder in one click.
- **Order lifecycle**: Processing → Dispatched → Delivered, with a timeline, driver and ETA on dispatch, proof of delivery and printable invoices.
- **Payments**: MTN Mobile Money, Airtel Money, Trade Credit Line, Cash on Delivery, plus bank transfer details and an outstanding-balance view.
- **Seller control center**: confirm orders, mark as paid, dispatch, deliver and cancel with reasons.
- **Inventory**: batch and expiry tracking (stock allocated per batch), reorder levels, goods receiving and a **demand forecast** tab.
- **Outlets and credit lines**: manage customer accounts and trade credit balances.
- **Support tickets**, **audit trail** and order logs.
- **Notifications**: in-app alerts, SMTP email and Meta WhatsApp Cloud API messages.
- **Accounts**: sign-up, login with brute-force lockout, PBKDF2 password hashing (600,000 iterations), email password-reset codes, and Customer vs Staff/Admin roles.
- **Dashboard** with KPIs and stock-out warnings from the forecast.

### Demand forecasting (`forecast.py`)

- Weekly per-product demand model using **LightGBM** (falls back to scikit-learn `HistGradientBoostingRegressor` if LightGBM isn't installed).
- Features: 1 to 4 week lags, 4 and 8 week rolling means, seasonality (week of year) and price.
- Outputs 4-week forecast, weeks of cover, a suggested reorder quantity and a risk label (OK / Watch / Stockout soon).
- **Demo mode:** until the shop has 8 weeks of real orders, the forecast is trained on *simulated* history (rainy-season peaks for malaria and diarrhoea items). It switches to real order data automatically afterwards.

### WhatsApp and payments backend (`app/`)

- **WhatsApp webhook**: shop owners message the bot to `search <medicine>` and `order <item id> <qty>`; orders are written to Supabase.
- **MTN MoMo** `requestToPay` helper (sandbox or production).
- **Micro-credit engine**: 7-day trade credit based on order history and repayment score (details below).
- **Data models**: `DrugOutlet`, `InventoryItem`, `Order`, `OrderItem` (SQLAlchemy).

---

## Project structure

```
.
├── streamlit_app.py        # Single-file Streamlit web app
├── forecast.py             # Demand forecasting model + forecast tab
├── requirements.txt        # Web app dependencies
├── medsupply_db.json       # Local data file (created automatically if Supabase isn't configured)
├── demand_model.joblib     # Trained forecast model (created automatically)
└── app/                    # WhatsApp / MoMo backend (FastAPI)
    ├── __init__.py
    ├── main.py             # FastAPI entry point
    ├── config.py           # Settings loaded from .env
    ├── models.py           # SQLAlchemy models
    ├── supabase_client.py  # Async Supabase client (see "Known issues")
    ├── routers/
    │   └── webhook.py      # WhatsApp webhook
    └── services/
        ├── whatsapp.py     # WhatsApp Cloud API sender
        ├── momo.py         # MTN MoMo collections
        └── credit_engine.py
```

---

## Getting started: web app

### 1. Install

```bash
pip install -r requirements.txt
# optional, faster forecasting:
pip install lightgbm
```

### 2. Configure secrets

Create `.streamlit/secrets.toml` locally, or paste the same content into **Streamlit Cloud → Settings → Secrets**:

```toml
ADMIN_EMAIL    = "you@example.com"
ADMIN_PASSWORD = "a-long-random-password"
DEMO_DATA      = false          # true = sample customer/orders and fake payments (testing only)
SUPABASE_URL   = "https://xxxx.supabase.co"
SUPABASE_KEY   = "<service_role key, server-side only>"
COMPANY_TIN    = "your URA TIN"  # optional, printed on invoices

# Needed for order emails and password reset
[smtp]
email    = "..."
password = "..."
server   = "smtp.gmail.com"
port     = 465

# Optional WhatsApp alerts (Meta Cloud API)
WHATSAPP_PHONE_NUMBER_ID = "..."
WHATSAPP_TOKEN           = "..."
```

If `ADMIN_PASSWORD` is not set, a one-time admin password is generated and printed to the server logs on first start.

### 3. Set up Supabase (one time)

Run in the Supabase SQL editor:

```sql
create table app_state (
  id text primary key,
  data text not null,
  updated_at timestamptz default now()
);
alter table app_state enable row level security;
```

The app stores its state as one JSON document in this table. Without Supabase credentials it falls back to a local `medsupply_db.json` file (fine for development, but data is lost on hosts with ephemeral storage such as Streamlit Cloud).

### 4. Run

```bash
streamlit run streamlit_app.py
```

To pre-train the forecast model and see its accuracy against a naive baseline:

```bash
python forecast.py
```

### Deploy

Push to GitHub, create an app on [Streamlit Community Cloud](https://streamlit.io/cloud) pointing at `streamlit_app.py`, then add your secrets.

---

## Getting started: WhatsApp / MoMo backend

### 1. Install

The backend needs packages that are **not** in the web app's `requirements.txt`:

```bash
pip install fastapi uvicorn httpx supabase pydantic-settings sqlalchemy
```

### 2. Environment variables

Create a `.env` file in the project root (never commit it):

```env
SUPABASE_URL=...
SUPABASE_KEY=...
SUPABASE_SERVICE_ROLE_KEY=...
DATABASE_URL=...

WHATSAPP_TOKEN=...
WHATSAPP_PHONE_NUMBER_ID=...
WHATSAPP_VERIFY_TOKEN=<choose-a-long-random-string>

MOMO_SUBSCRIPTION_KEY=...
MOMO_API_USER=...
MOMO_API_KEY=...
MOMO_TARGET_ENV=sandbox      # "sandbox" or production
```

### 3. Run and connect WhatsApp

```bash
uvicorn app.main:app --reload
```

Expose the server over HTTPS (for example with ngrok), then in the Meta developer dashboard set the webhook URL to `https://<your-domain>/webhook` and use your `WHATSAPP_VERIFY_TOKEN` as the verify token.

### WhatsApp commands

| Message | Result |
|---|---|
| `search coartem` | Lists up to 5 matching medicines with price and supplier |
| `order 12 5` | Creates an order for 5 units of item ID 12 and replies with a confirmation |

Only shops registered in the `drug_outlets` table (matched by WhatsApp number) can order.

---

## Credit engine rules

Implemented in `credit_engine.py`:

- Requires at least **3 completed orders** and an on-time repayment score of at least **0.8**, otherwise the limit is 0.
- Limit = average order value × multiplier × repayment score, where the multiplier is **0.3** (fewer than 10 orders) or **0.5** (10 or more).
- Capped at **UGX 2,000,000**.

---

## Tech stack

- **Web app:** Streamlit, pandas, requests, SMTP
- **ML:** scikit-learn, LightGBM (optional), joblib, NumPy
- **Backend:** FastAPI, httpx, SQLAlchemy, pydantic-settings
- **Data:** Supabase (PostgreSQL)
- **Integrations:** Meta WhatsApp Cloud API, MTN Mobile Money API

---

## Known issues and roadmap

- **Import mismatch:** `main.py` and `webhook.py` import `app.supabase_client`, but the file is named `database.py`. Rename it to `supabase_client.py` (and place `whatsapp.py`, `momo.py` and `credit_engine.py` in `app/services/`, `webhook.py` in `app/routers/`) so the backend starts.
- **Backend not yet connected to the web app:** the Streamlit app stores data in `app_state`, while the backend uses relational tables (`drug_outlets`, `inventory_items`, `orders`, `order_items`). Orders placed on WhatsApp won't appear in the web app until they share one data store.
- **Unwired modules:** `momo.py`, `credit_engine.py` and the WhatsApp interactive payment buttons exist but aren't called by the webhook yet. Order status isn't updated after a MoMo payment, and there's no MoMo callback endpoint.
- **Webhook security:** add verification of Meta's `X-Hub-Signature-256` header on `POST /webhook`, and don't rely on the default verify token in `config.py`.
- **Demo data:** with `DEMO_DATA` unset the app seeds a sample customer with a known password. Set `DEMO_DATA = false` in production.
- **Tax:** `VAT_RATES` is intentionally empty. Confirm the treatment for each category with URA or your accountant before enabling.
- **Forecast accuracy figures** printed by `python forecast.py` are measured on simulated data and say nothing about real-world accuracy yet.

---

## Security notes

- Never commit `.env`, `secrets.toml` or any API keys. Add them to `.gitignore`.
- `SUPABASE_KEY` for the web app must be the **service_role** key and stays server-side only. Keep Row Level Security enabled on `app_state`.
- Rotate any key that has ever been pushed to a public repository.

---

## Author

**Okiror Innocent**, Computer Science student, Mbarara University of Science and Technology (MUST), Uganda.

## License

© 2026 MedSupply Uganda. All rights reserved.
