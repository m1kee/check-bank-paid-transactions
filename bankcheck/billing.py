"""
What the next statement will charge, for cards paid by statement balance (USD).

The bank's download is the "Saldos y Movimientos No Facturados" view: the
purchases in the latest download of a currency are exactly what the next
statement will bill. The history knows which movements came in each download
(movements.last_import_id), so no cut-off date has to be configured.
"""
import datetime
import sqlite3
from dataclasses import dataclass

import pandas as pd

from bankcheck import config, history
from bankcheck.matching import is_payment_description


@dataclass(frozen=True)
class UpcomingStatement:
    currency: str
    amount: float
    count: int  # purchases (refunds included)
    since: pd.Timestamp  # oldest purchase in the view, None if there are none
    seen_at: datetime.datetime  # when the download was imported


def statement_currencies() -> list:
    return [currency for currency, mode in config.MATCHING_MODE.items() if mode == "statement"]


def upcoming_statement(view: pd.DataFrame, currency: str, seen_at: datetime.datetime) -> UpcomingStatement:
    """The total of the purchases in one download of the unbilled view (payments left out)."""
    rows = view[view["Currency"] == currency]
    purchases = rows[~rows["Description"].map(is_payment_description).astype(bool)]
    return UpcomingStatement(
        currency=currency,
        amount=round(float(purchases["Amount"].sum()), 2),
        count=len(purchases),
        since=purchases["Date"].min() if not purchases.empty else None,
        seen_at=seen_at,
    )


def load_upcoming(conn: sqlite3.Connection, movements: pd.DataFrame = None) -> list:
    """One UpcomingStatement per statement-paid currency with downloads in the history."""
    movements = history.load_movements(conn) if movements is None else movements
    found = []
    for currency in statement_currencies():
        row = conn.execute(
            "SELECT i.id, i.imported_at FROM imports i WHERE i.id = "
            "(SELECT MAX(last_import_id) FROM movements WHERE currency = ?)",
            (currency,),
        ).fetchone()
        if row is None:
            continue
        import_id, imported_at = row
        ids = {i for (i,) in conn.execute(
            "SELECT id FROM movements WHERE currency = ? AND last_import_id = ?", (currency, import_id)
        )}
        view = movements[movements["Id"].isin(ids)]
        found.append(upcoming_statement(view, currency, datetime.datetime.fromisoformat(imported_at)))
    return found
