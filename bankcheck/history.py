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

import pandas as pd

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
