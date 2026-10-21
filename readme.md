# 🚀 Account Analysis Tool

A Python utility to process and analyze the bank's **current-period movements view** (the "al día" download, not the monthly statement). It reads the raw `.xls` export, finds single-installment purchases that don't have a matching payment yet, and generates an HTML report.

Current version: see [`CHANGELOG.md`](CHANGELOG.md) · Roadmap: [`feature-proposals/`](feature-proposals/README.md)

## ✨ Features

* **Format detection:** finds the movements section and its header by name ("Movimientos Nacionales" / "Movimientos Internacionales") and fails with a clear error if the bank changes the layout.
* **Pesos and dollars:** each movement carries its currency, and each currency is reconciled separately (dollar support not yet validated with a real file).
* **Date-aware matching:** a payment only covers a purchase of the same amount made before it (or the same day), within a configurable window; repeated amounts are paid oldest first.
* **Several downloads at once:** movements repeated across downloads are counted once.
* **Audit info:** lists unpaid purchases and payments that didn't match any purchase.
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
|   |-- matching.py      Pair purchases with payments
|   |-- analysis.py      Per-currency analysis and totals
|   |-- formatting.py    Currency formatting
|   |-- report_html.py   HTML report rendering
|-- tests/               Unit tests (synthetic data only)
|-- feature-proposals/   Roadmap and feature ideas
|-- CHANGELOG.md
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
* `input_files`: one or more raw files (`.xls`/`.xlsx`). Pass the pesos and dollars files together to get a single report.
* `-o, --output`: optional prefix for the clean `.xlsx` file (default `cleaned-movements`).
* `-d, --start-date`: ignore movements before this date (`YYYY-MM-DD`).
* `--version`: print the version.

Examples:
```bash
uv run bankcheck pre-process-data/pesos.xls pre-process-data/dolares.xls
uv run bankcheck pre-process-data/pesos.xls -d 2026-10-01 -o october
```

The tool will:
1. Read every file (and stop without moving anything if one can't be read).
2. Save the clean movements to `data/<prefix>_<timestamp>.xlsx`.
3. Move the raw files to `processed-archive/movements_<timestamp>.xls`.
4. Print the analysis and open `reports/report_<timestamp>.html`.

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
