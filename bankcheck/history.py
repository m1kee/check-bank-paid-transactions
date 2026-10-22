"""
Persistent history of movements in SQLite.

Each download of the movements view is imported once; movements already in the
history (same fingerprint, see dedup.py) are only marked as seen again. The
analysis then runs over the whole history, so a purchase that is still unpaid
keeps showing up after the bank closes the period and drops it from the view.
"""
import datetime
import logging
import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from bankcheck import config
from bankcheck.dedup import add_fingerprints
from bankcheck.parsers import COLUMNS


log = logging.getLogger(__name__)


class HistoryError(Exception):
    """The history database can't be used."""


# Each script upgrades the schema from version i to i + 1 (PRAGMA user_version).
# Never edit a released migration: append a new one.
MIGRATIONS = [
    """
    CREATE TABLE imports (
        id INTEGER PRIMARY KEY,
        imported_at TEXT NOT NULL,
        source_name TEXT,
        sha256 TEXT,
        new_count INTEGER NOT NULL DEFAULT 0,
        existing_count INTEGER NOT NULL DEFAULT 0
    );

    CREATE TABLE movements (
        id INTEGER PRIMARY KEY,
        currency TEXT NOT NULL,
        date TEXT NOT NULL,
        card_type TEXT NOT NULL DEFAULT '',
        description TEXT NOT NULL DEFAULT '',
        city TEXT NOT NULL DEFAULT '',
        installments TEXT NOT NULL DEFAULT '',
        installment_details TEXT NOT NULL DEFAULT '',
        amount NUMERIC NOT NULL,
        fingerprint TEXT NOT NULL UNIQUE,
        first_import_id INTEGER NOT NULL REFERENCES imports(id),
        last_import_id INTEGER NOT NULL REFERENCES imports(id),
        first_seen_at TEXT NOT NULL,
        last_seen_at TEXT NOT NULL
    );

    CREATE INDEX movements_currency_date ON movements(currency, date);
    """,
]


def _sql_text(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _seed_categories_sql(categories: dict) -> str:
    """INSERTs for the starting categories and rules (config.DEFAULT_CATEGORIES)."""
    statements = []
    for name, patterns in categories.items():
        statements.append(f"INSERT INTO categories (name) VALUES ({_sql_text(name)});")
        for pattern in patterns:
            statements.append(
                "INSERT OR IGNORE INTO category_rules (pattern, category_id, created_at) "
                f"SELECT {_sql_text(pattern.upper())}, id, datetime('now') FROM categories "
                f"WHERE name = {_sql_text(name)};"
            )
    return "\n".join(statements)


# v2: manual reconciliation (03, 11), categories (13) and budgets (30). The
# starting categories are the ones in config at the time the history is migrated.
MIGRATIONS.append(
    """
    CREATE TABLE resolutions (
        movement_id INTEGER PRIMARY KEY REFERENCES movements(id) ON DELETE CASCADE,
        status TEXT NOT NULL CHECK (status IN ('paid', 'ignored')),
        payment_id INTEGER REFERENCES movements(id) ON DELETE CASCADE,
        reason TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL
    );

    CREATE TABLE dismissed_suggestions (
        payment_id INTEGER PRIMARY KEY REFERENCES movements(id) ON DELETE CASCADE,
        created_at TEXT NOT NULL
    );

    CREATE TABLE categories (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL UNIQUE COLLATE NOCASE,
        budget NUMERIC
    );

    CREATE TABLE category_rules (
        id INTEGER PRIMARY KEY,
        pattern TEXT NOT NULL UNIQUE COLLATE NOCASE,
        category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
        created_at TEXT NOT NULL
    );

    ALTER TABLE movements ADD COLUMN category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL;
    """
    + _seed_categories_sql(config.DEFAULT_CATEGORIES)
)

# v3: notifications already sent, so budgets and alerts are announced once (20)
MIGRATIONS.append(
    """
    CREATE TABLE notifications (
        key TEXT PRIMARY KEY,
        sent_at TEXT NOT NULL
    );
    """
)

# DataFrame column -> movements table column
_DB_COLUMNS = {
    "Currency": "currency",
    "Date": "date",
    "Card Type": "card_type",
    "Description": "description",
    "City": "city",
    "Installments": "installments",
    "Installment Details": "installment_details",
    "Amount": "amount",
}


@dataclass
class ImportResult:
    import_id: int
    new_count: int
    existing_count: int


def connect(path: str) -> sqlite3.Connection:
    """Open (and create or upgrade, if needed) the history database at `path`."""
    if path != ":memory:":
        folder = os.path.dirname(path)
        if folder:
            os.makedirs(folder, exist_ok=True)
    try:
        conn = sqlite3.connect(path)
    except sqlite3.Error as e:
        raise HistoryError(f"No se pudo abrir el historial '{path}': {e}") from e
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        migrate(conn)
    except Exception:
        conn.close()
        raise
    return conn


def connect_copy(path: str) -> sqlite3.Connection:
    """
    An in-memory copy of the history at `path` (empty if it doesn't exist), so
    a dry run can import and analyze without touching the file.
    """
    copy = sqlite3.connect(":memory:")
    if os.path.exists(path):
        try:
            source = sqlite3.connect(f"file:{Path(path).resolve().as_posix()}?mode=ro", uri=True)
            try:
                source.backup(copy)
            finally:
                source.close()
        except sqlite3.Error as e:
            copy.close()
            raise HistoryError(f"No se pudo leer el historial '{path}': {e}") from e
    copy.execute("PRAGMA foreign_keys = ON")
    migrate(copy)
    return copy


def schema_version(conn: sqlite3.Connection) -> int:
    return conn.execute("PRAGMA user_version").fetchone()[0]


def migrate(conn: sqlite3.Connection):
    """Apply the migrations the database doesn't have yet."""
    version = schema_version(conn)
    if version > len(MIGRATIONS):
        raise HistoryError(
            f"El historial usa el esquema v{version}, más nuevo que el de esta versión del programa "
            f"(v{len(MIGRATIONS)}). Actualiza bankcheck."
        )
    for target, script in enumerate(MIGRATIONS[version:], start=version + 1):
        log.debug("Migrando el historial al esquema v%d", target)
        # executescript ignores the connection's transaction handling, so the
        # script carries its own: a failed migration leaves the schema untouched
        conn.executescript(f"BEGIN;\n{script}\nPRAGMA user_version = {target};\nCOMMIT;")


def _native(value):
    """numpy scalars -> plain Python values, which sqlite3 can store."""
    return value.item() if hasattr(value, "item") else value


def import_movements(
    conn: sqlite3.Connection,
    movements: pd.DataFrame,
    source_name: str = None,
    sha256: str = None,
    now: datetime.datetime = None,
) -> ImportResult:
    """
    Add one download to the history. Movements already in it are not duplicated:
    only their last-seen import and timestamp are updated.
    """
    seen_at = (now or datetime.datetime.now()).isoformat(timespec="seconds")
    df = add_fingerprints(movements)

    columns = list(_DB_COLUMNS.values())
    insert = (
        f"INSERT OR IGNORE INTO movements ({', '.join(columns)}, fingerprint, "
        "first_import_id, last_import_id, first_seen_at, last_seen_at) "
        f"VALUES ({', '.join('?' * len(columns))}, ?, ?, ?, ?, ?)"
    )
    touch = "UPDATE movements SET last_import_id = ?, last_seen_at = ? WHERE fingerprint = ?"

    with conn:
        import_id = conn.execute(
            "INSERT INTO imports (imported_at, source_name, sha256) VALUES (?, ?, ?)",
            (seen_at, source_name, sha256),
        ).lastrowid

        new_count = 0
        for record in df.to_dict("records"):
            values = [_native(record[name]) for name in _DB_COLUMNS]
            values[1] = pd.Timestamp(record["Date"]).strftime("%Y-%m-%d")
            fingerprint = record["Fingerprint"]
            cursor = conn.execute(insert, (*values, fingerprint, import_id, import_id, seen_at, seen_at))
            if cursor.rowcount:
                new_count += 1
            else:
                conn.execute(touch, (import_id, seen_at, fingerprint))

        existing_count = len(df) - new_count
        conn.execute(
            "UPDATE imports SET new_count = ?, existing_count = ? WHERE id = ?",
            (new_count, existing_count, import_id),
        )

    return ImportResult(import_id=import_id, new_count=new_count, existing_count=existing_count)


def recent_imports(conn: sqlite3.Connection, limit: int = 8) -> list:
    """The latest imports, newest first, as dicts with "imported_at", "source_name", "new_count", "existing_count"."""
    rows = conn.execute(
        "SELECT imported_at, source_name, new_count, existing_count FROM imports ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    return [
        {"imported_at": datetime.datetime.fromisoformat(at), "source_name": name or "", "new_count": new, "existing_count": old}
        for at, name, new, old in rows
    ]


def load_movements(conn: sqlite3.Connection, currency: str = None) -> pd.DataFrame:
    """
    Every movement in the history (optionally of one currency), sorted by date,
    with the normalized columns plus "Id", "First Seen" and "Last Seen".
    """
    query = (
        f"SELECT id, {', '.join(_DB_COLUMNS.values())}, first_seen_at, last_seen_at FROM movements"
    )
    params = ()
    if currency is not None:
        query += " WHERE currency = ?"
        params = (currency,)
    query += " ORDER BY date, id"

    rows = conn.execute(query, params).fetchall()
    df = pd.DataFrame(rows, columns=["Id", *_DB_COLUMNS, "First Seen", "Last Seen"])
    df["Date"] = pd.to_datetime(df["Date"], format="%Y-%m-%d")
    df["Amount"] = pd.to_numeric(df["Amount"])
    for name in ("First Seen", "Last Seen"):
        df[name] = pd.to_datetime(df[name], format="ISO8601")
    return df[["Id", *COLUMNS, "First Seen", "Last Seen"]]
