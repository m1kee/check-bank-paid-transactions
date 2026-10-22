# 🚀 Account Analysis Tool

A Python utility to process and analyze the bank's **current-period movements view** (the "al día" download, not the monthly statement). It reads the raw `.xls` export, finds single-installment purchases that don't have a matching payment yet, and generates an HTML report.

Current version: see [`CHANGELOG.md`](CHANGELOG.md) · Roadmap: [`feature-proposals/`](feature-proposals/README.md)

## ✨ Features

* **Format detection:** finds the movements section and its header by name ("Movimientos Nacionales" / "Movimientos Internacionales") and fails with a clear error if the bank changes the layout.
* **Pesos and dollars:** each movement carries its currency, and each currency is reconciled separately. Pesos are paid purchase by purchase; dollars are paid by statement balance, so a dollar payment covers the run of consecutive purchases that adds up to it (`MATCHING_MODE` in `config.py`). For dollars the app also shows the **next statement**: the total of the purchases in your latest download, which is the bank's unbilled view.
* **Notifications (ntfy):** after each upload, a summary of what's pending on your phone, plus a one-time notice when a budget passes 80%/100% or a charge looks duplicated. Free, off by default.
* **Date-aware matching:** a payment only covers a purchase of the same amount made before it (or the same day), within a configurable window; repeated amounts are paid oldest first.
* **Several downloads at once:** movements repeated across downloads are counted once.
* **History (`--db`):** every download is imported into a SQLite database, so an unpaid purchase stays pending after the bank closes the period, and a payment in the next period can cover it.
* **Web app (`bankcheck-web`):** upload downloads from any device, see unpaid purchases and browse the history. Mobile-first, works without JavaScript.
* **Audit info:** lists unpaid purchases, payments that didn't match any purchase, and which payment covered each purchase.
* **Manual reconciliation:** mark a purchase as paid or ignored (with a reason), or ignore a payment; stored in the history and undoable.
* **Grouped payments:** a payment equal to the sum of 2–4 unpaid purchases is *suggested* (never applied on its own) so you can accept it.
* **Categories and budgets:** every movement gets a category from editable rules (the longest match wins); change one in the web app and it offers to learn a rule. Monthly budgets per category show whether you're ahead of the month's pace.
* **Charts:** spending by day and by category (vs the previous month), and pending amount by age; plain HTML/CSS, offline.
* **Installments, subscriptions and alerts:** remaining debt per installment purchase and a 12-month projection; recurring monthly charges with price increases; possible duplicates, unusual amounts and new merchants/cities.
* **Share the pending list:** copy it as text (ready for WhatsApp) or download a CSV, from the web app, the HTML report or `--export`.
* **HTML report:** self-contained dark-mode page that works offline and opens in the browser.
* **File archiving:** raw inputs are moved to `processed-archive/` with a timestamp; a clean `.xlsx` (real dates) is saved to `data/`.
* **Configurable:** payment terms, exclusions, matching window and file layout live in `bankcheck/config.py`.

---

## 📂 Project Structure

```
check-bank-paid-transactions/
|-- pyproject.toml       Project metadata, dependencies and version
|-- uv.lock              Exact dependency versions
|-- bankcheck/           Core logic, reusable by the CLI and the future web app
|   |-- cli.py           CLI entry point (the `bankcheck` command)
|   |-- config.py        Settings: file formats, payment terms, matching window
|   |-- parsers.py       Read the bank export into a normalized DataFrame
|   |-- dedup.py         Merge downloads without duplicating movements
|   |-- history.py       SQLite history of every imported movement
|   |-- reconcile.py     Manual resolutions and grouped-payment suggestions
|   |-- categories.py    Category rules, spending and budgets
|   |-- installments.py  Purchases in installments
|   |-- recurring.py     Subscriptions and recurring charges
|   |-- alerts.py        Duplicates, unusual amounts, new merchants and cities
|   |-- insights.py      Everything above, together, for the home page and the report
|   |-- charts.py        HTML/CSS charts
|   |-- export.py        Pending list as text and CSV
|   |-- text.py          Description normalization helpers
|   |-- matching.py      Pair purchases with payments
|   |-- analysis.py      Per-currency analysis and totals
|   |-- formatting.py    Currency formatting
|   |-- report_html.py   HTML report rendering
|   |-- web/             Web app (FastAPI + Jinja2 + HTMX)
|-- tests/               Unit tests (synthetic data only)
|-- feature-proposals/   Roadmap and feature ideas
|-- CHANGELOG.md
|-- Dockerfile         Web app image
|-- docker-compose.yml Runs the web app with the data in ./data
|
|-- pre-process-data/    Put your raw .xls downloads here (git-ignored)
|-- data/                Clean .xlsx files (git-ignored)
|-- processed-archive/   Archived raw files (git-ignored)
|-- reports/             HTML reports (git-ignored)
```

---

## 🔧 Installation & Setup

The project is managed with [uv](https://docs.astral.sh/uv/).

1.  **Install uv** (once per machine):
    ```bash
    # macOS
    brew install uv

    # Windows (PowerShell)
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    ```

2.  **Clone and install:**
    ```bash
    git clone git@github.com:m1kee/check-bank-paid-transactions.git
    cd check-bank-paid-transactions
    uv sync
    ```
    `uv sync` creates `.venv/`, installs the right Python version if needed and the exact dependency versions from `uv.lock`. No need to activate the environment: prefix commands with `uv run`.

---

## ⚙️ How to Use

Download the movements view from the bank (pesos and/or dollars), put the files in `pre-process-data/` and run:

```bash
uv run bankcheck pre-process-data/movimientos.xls
```

Arguments:
* `input_files`: one or more raw files (`.xls`/`.xlsx`). Pass the pesos and dollars files together to get a single report. Without files, every download waiting in `pre-process-data/` is processed.
* `-o, --output`: optional prefix for the clean `.xlsx` file (default `cleaned-movements`).
* `-d, --start-date` / `-e, --end-date`: analyze only this range (`YYYY-MM-DD`, both inclusive).
* `--db [RUTA]`: import the files into the history (default `data/bank.db`) and analyze the whole history instead of only these downloads. Without files, it just re-analyzes the history.
* `--no-open`: write the HTML report but don't open the browser.
* `--no-archive`: leave the input files where they are.
* `--dry-run`: write nothing at all (no clean file, archive, report or history changes); just print the analysis.
* `--reanalyze ARCHIVO`: analyze a clean `.xlsx` from `data/` instead of bank downloads.
* `--export ARCHIVO.csv`: save the pending purchases as CSV.
* `-v, --verbose` / `-q, --quiet`: more detail (debugging) / only the report, warnings and errors.
* `--version`: print the version.

Examples:
```bash
uv run bankcheck pre-process-data/pesos.xls pre-process-data/dolares.xls
uv run bankcheck pre-process-data/pesos.xls -d 2026-10-01 -o october
uv run bankcheck pre-process-data/pesos.xls --db   # add to the history and check it
uv run bankcheck --db                              # check the history only
```

The tool will:
1. Read every file (and stop without moving anything if one can't be read).
   With `--db`, add them to the history (`N movimientos nuevos, M ya existían`).
2. Save the clean movements to `data/<prefix>_<timestamp>.xlsx`.
3. Move the raw files to `processed-archive/movements_<timestamp>.xls`.
4. Print the analysis and open `reports/report_<timestamp>.html`.

Progress messages go to stderr and the analysis to stdout, so `uv run bankcheck x.xls -q > analisis.txt` saves just the report. The exit code is `1` when a file or the history can't be read.

---

## 🌐 Web App

```bash
uv run bankcheck-web                    # http://127.0.0.1:8000
uv run bankcheck-web --host 0.0.0.0     # reachable from other devices on the network
uv run bankcheck-web --reload           # restart on code changes (development)
```

Pages:
* **Inicio** (`/dashboard`): spending of the month vs the previous one, budgets, alerts and charts.
* **Pendientes** (`/pending`): unpaid purchases over the whole history, with totals, age and a date range; resolve them by hand, accept grouped-payment suggestions, see which payment covered each purchase, copy the list or download a CSV.
* **Subir** (`/upload`): upload one or more `.xls`/`.xlsx` downloads; shows how many movements were new. If one file can't be read, nothing is imported.
* **Movimientos** (`/movements`): the whole history, with search and currency/category/date filters; change a movement's category in place.
* **Cuotas** (`/installments`): installment purchases still running, monthly commitment, remaining debt and projection.
* **Suscripciones** (`/subscriptions`): recurring monthly charges, yearly cost and price increases.
* **Categorías** (`/categories`): categories, budgets, rules, merging categories and the merchants still without one.

It uses the same history as `bankcheck --db`. Settings, through environment variables:

| Variable | Default | |
|---|---|---|
| `BANKCHECK_DATA_DIR` | `data` | Base folder for the clean files, the history and the uploads (also used by the CLI) |
| `BANKCHECK_DB` | `<data dir>/bank.db` | SQLite history |
| `BANKCHECK_UPLOADS_DIR` | `<data dir>/uploads` | Uploaded original files |
| `BANKCHECK_PASSWORD` | *(none)* | If set, every page asks for it (any user name) |
| `BANKCHECK_NTFY_URL` | *(off)* | ntfy topic for notifications, e.g. `https://ntfy.sh/<long-secret-topic>` |
| `BANKCHECK_NTFY_TOKEN` | *(none)* | Access token, only for a protected (self-hosted) ntfy server |
| `BANKCHECK_NOTIFY_DETAILS` | *(off)* | `1` to include merchants in notifications, not just counts and totals |

Set a password whenever the app listens on anything other than `127.0.0.1`.

### Notifications

[ntfy](https://ntfy.sh) is free and needs no account: install the app, subscribe to a topic with a long random name (anyone who knows it can read it) and set `BANKCHECK_NTFY_URL`. The **Subir** page has a button to send a test. Messages only carry counts and totals unless `BANKCHECK_NOTIFY_DETAILS=1`.

### Docker

```bash
echo "BANKCHECK_PASSWORD=una-clave-larga" > .env   # required; .env is git-ignored
mkdir -p data                                     # history and uploads, mounted at /data
docker compose up -d --build                      # http://127.0.0.1:8000
docker compose logs -f                            # see imports and requests
```

The port is published on `127.0.0.1` only. To reach it from other devices, set `BANKCHECK_BIND` in `.env` (e.g. the machine's Tailscale IP) or put `tailscale serve 8000` in front of it. `BANKCHECK_PORT` and `TZ` (default `America/Santiago`) can also go in `.env`. To update: `git pull && docker compose up -d --build`.

---

## 🧪 Tests

```bash
uv run python -m unittest -v
```

Tests use synthetic data shaped like the bank export; never commit real bank files. GitHub Actions runs them on every push.

## 🏷️ Versioning

The version lives in `pyproject.toml` and follows [Semantic Versioning](https://semver.org/). To release:

1. Bump it: `uv version --bump minor` (or `patch` / `major`).
2. Move the `[Unreleased]` notes in [`CHANGELOG.md`](CHANGELOG.md) under the new version (a test fails if the entry is missing).
3. Commit and tag `vX.Y.Z`.

## 📦 Dependencies

```bash
uv add <package>          # add a dependency
uv lock --upgrade         # upgrade everything within the allowed ranges
```
