# SmartElec — Secure Smart Electricity Consumption Analysis System

A Flask app that lets a household register, log in with OTP, record which
appliances they own, upload a photo of their electricity bill (or an SMS
screenshot), and get a simple AI-based usage prediction and appliance-based
recommendations.

## How the flow works

1. **Register** → **log in** with username/password → **OTP** verification
   (email or SMS — see [OTP delivery](#otp-delivery) below).
2. **First login only**: redirected to the appliance profile to select which
   appliances the household owns. This is skipped on every login after the
   first — `user.first_login_done` in the database tracks this, not a
   session flag, so it survives across devices and logins.
3. **Upload** a bill photo or SMS screenshot. The server runs OCR
   (`pytesseract`) to extract units consumed, the bill amount, and the
   billing period, then shows those values for review — nothing is saved to
   the database until you confirm/edit and submit.
4. The confirmed bill immediately shows up on the **dashboard**: this
   month's usage, estimated bill, a bar chart of recent months, and a
   prediction preview.
5. **AI prediction** (needs at least 2 confirmed bills) and
   **recommendations** (rule-based, matched against your appliance profile)
   are both available once there's enough history.

## Project structure

```
project_root/
├── app.py                  # Flask app factory — registers every blueprint
├── page_routes.py          # Renders the 12 HTML templates, with session guards
├── config/config.py        # All settings, read from environment variables
├── database/
│   ├── db.py                # Shared SQLAlchemy instance
│   └── schema.sql           # Source of truth for the real database schema
├── models/                 # User, Otp, Appliance, ApplianceProfile, Bill, Prediction, LoginLog
├── routes/                 # One blueprint per flow step (see below)
├── utils/                  # email_utils, login_utils, ocr_utils, ml_utils
├── ml_models/               # Drop trained .pkl files here (see note below)
├── templates/               # The 12 pages
├── static/css/ + static/js/
└── uploads/
    ├── sample_bills/         # test images
    └── temp/                 # OCR staging — files are deleted right after extraction
```

| Blueprint | URL prefix | Covers |
|---|---|---|
| `page_routes.py` | *(none)* | Renders templates, session-based access guards |
| `routes/auth_routes.py` | `/auth` | Register, login, OTP verify/resend, logout |
| `routes/appliance_routes.py` | `/appliances` | Onboarding + profile editing (same endpoints) |
| `routes/bill_routes.py` | `/bill` | Upload → OCR → confirm → recent bills |
| `routes/dashboard_routes.py` | `/dashboard` | Stats, chart data, recent bills |
| `routes/predict_routes.py` | `/predict` | Full AI prediction + accuracy tracking |
| `routes/report_routes.py` | `/reports` | Year-filtered bill history + summary |
| `routes/profile_routes.py` | `/profile` | Account info, password change, data export |

## Setup

### 1. Install dependencies

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

You'll also need the **Tesseract OCR** binary installed separately (it's
what `pytesseract` calls out to) — `pytesseract` alone isn't enough:

- macOS: `brew install tesseract`
- Ubuntu/Debian: `sudo apt install tesseract-ocr`
- Windows: install from [UB-Mannheim's build](https://github.com/UB-Mannheim/tesseract/wiki),
  then set `TESSERACT_CMD` in `.env` to the install path.

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and set at minimum:
- `SECRET_KEY` — any long random string
- `DATABASE_URL` — your MySQL connection string
- `OTP_CHANNEL` — `email` or `sms`, plus the matching credentials below it

If you leave the mail/SMS credentials blank, OTP codes are logged to the
**Flask server's console** instead of actually being delivered — useful for
local development, but you won't see the code anywhere in the browser (this
is intentional — see the note in `otp.js`).

### 3. Create the database

```bash
mysql -u root -p -e "CREATE DATABASE smartelec_dev"
mysql -u root -p smartelec_dev < database/schema.sql
```

### 4. Run it

```bash
flask run
```

Visit `http://127.0.0.1:5000/` — it redirects to registration if you're not
logged in.

## Testing status

Every backend route was tested during development using a lightweight fake
ORM standing in for SQLAlchemy (this environment doesn't have network access
to install `flask-sqlalchemy` directly), run through Flask's real test
client against the actual route code — not against mocked route logic. That
gives confidence the *logic* is correct, but it is **not** a substitute for
testing against real MySQL, since SQL-specific behavior (unique constraint
races, connection pooling, actual `ENUM`/`DECIMAL` type coercion) isn't
exercised by the fakes.

**Before relying on this for anything real, at minimum:**
- Run through the full register → OTP → onboarding → upload → confirm →
  dashboard flow in an actual browser against the real database.
- Upload a real bill photo and check the OCR extraction quality —
  `utils/ocr_utils.py`'s regex-based field extraction is a best-effort
  starting point (same approach the original prototype used with
  Tesseract.js), not a trained field extractor, so accuracy will vary a lot
  by bill layout.

## Known limitations

- **The 9 `.pkl` model files** this project was originally scoped around
  are not wired in. `utils/ml_utils.py` has a `load_pretrained_model()` hook
  ready for them, but nothing calls it yet — predictions currently run on a
  simple linear regression over your own confirmed bills
  (`predict_next_month()` in the same file), which is honest but simpler
  than whatever those trained models were meant to do.
- **Prediction accuracy tracking uses free-text matching.** `billing_period`
  is stored as whatever text was OCR'd or typed in (e.g. `"10 Jun 2024 - 09
  Jul 2024"`), not structured start/end dates. The accuracy log in
  `predict_routes.py` matches a prediction to a later real bill by exact
  text match on this field, so it will silently fail to score a prediction
  (not crash — just skip it) if formatting drifts. A schema change to real
  `start_date`/`end_date` columns would fix this properly.
- **Passwords are hashed** (`werkzeug.security`), but sessions use Flask's
  default signed-cookie sessions, which can't be revoked server-side. There
  is no "log out all other devices" feature for this reason — it would need
  a server-side session store to do properly.
- **OCR runs synchronously** inside the upload request — fine for a single
  user testing locally, but a production deployment handling multiple
  concurrent uploads would want this moved to a background task queue
  (Celery, RQ) rather than blocking the request thread.
