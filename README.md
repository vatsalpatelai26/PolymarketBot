# Polymarket Trader Tracker (Flask + SQLite)

This repo now contains a local web app that tracks selected Polymarket traders, stores their trades in SQLite, and shows trader profile details (username, profile image, bio, etc.) plus trade history.

## What is included

- `fetch_trades.py`: Fetches tracked traders' profiles + trades from Polymarket and writes to SQLite.
- `app.py`: Flask server that serves a plain HTML/CSS/JS dashboard and JSON APIs.
- `db.py`: Database schema + initialization.
- `tracked_traders.json`: List of wallet addresses to track.
- `templates/index.html`, `static/style.css`, `static/app.js`: Front-end UI.

## 1) Install Python (if you don't have it)

Install Python 3.10+ from https://www.python.org/downloads/ and ensure `python` works in your terminal.

## 2) Create and activate a virtual environment

From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
```

On Windows (PowerShell):

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

## 3) Install dependencies

```bash
pip install -r requirements.txt
```

## 4) Configure which traders to track

Edit `tracked_traders.json` and put real wallet addresses in the JSON array:

```json
[
  "0x123...",
  "0xabc..."
]
```

## 5) Initialize database (optional explicit step)

```bash
python db.py
```

This creates `polymarket.db` in the repo root.

## 6) Run the trade fetcher

### One-time sync

```bash
python fetch_trades.py
```

### Continuous sync every minute

```bash
python fetch_trades.py --loop
```

Keep this running in one terminal.

## 7) Run the Flask website

In another terminal (same virtual env):

```bash
python app.py
```

Open: http://127.0.0.1:5000

## How it works

- Every sync, the fetch script:
  - Loads addresses from `tracked_traders.json`.
  - Pulls profile information for each trader.
  - Pulls recent trades for each trader.
  - Upserts profile data into `traders` table.
  - Inserts new trades into `trades` table (deduplicated by `trade_id`).
- The web app reads from SQLite and displays:
  - Trader profile image, username/display name, bio, follower count, etc.
  - Latest trade list for the selected trader.


## One-command smoke test ("do it for me")

If you want an automated check, run:

```bash
python scripts/smoke_test.py
```

This script will:
- compile-check Python files
- initialize the SQLite DB
- run one sync fetch
- if Flask is installed, boot the server briefly and test `/api/traders` (+ one trader trades endpoint when available)

## Notes

- If Polymarket API fields/paths change, update endpoint/field mapping in `fetch_trades.py`.
- The dashboard displays what is in your local DB, so run fetcher first for data to appear.
