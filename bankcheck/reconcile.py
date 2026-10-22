"""
Manual reconciliation (proposal 03) and grouped payments (proposal 11).

Some cases the 1-to-1 matching can't solve: a purchase paid from another
account, one somebody else pays, a refund, or one payment that covered several
purchases. Those decisions are stored in the history as *resolutions*:

- a purchase marked "paid" (optionally by a given payment) or "ignored"
  stops being pending;
- a payment marked "ignored", or one that covers purchases through an accepted
  grouped suggestion, stops being an orphan payment.
"""
import datetime
import itertools
import sqlite3
from dataclasses import dataclass, field

import pandas as pd

from bankcheck import config

PAID = "paid"
IGNORED = "ignored"
STATUS_LABELS = {PAID: "Pagada a mano", IGNORED: "Ignorada"}

# Purchases considered for one grouped payment (the closest ones in date):
# keeps the number of combinations small enough to try them all
GROUP_MAX_CANDIDATES = 30

# Possible combinations shown for one payment before giving up
GROUP_MAX_OPTIONS = 5


@dataclass(frozen=True)
class Resolution:
    status: str
    reason: str = ""
    payment_id: int = None


@dataclass
class GroupSuggestion:
    """An orphan payment that equals the sum of some unpaid purchases."""

    payment: dict
    options: list = field(default_factory=list)  # each option: a list of purchase rows (dicts)

    @property
    def ambiguous(self) -> bool:
        return len(self.options) > 1


# --- Persistence -----------------------------------------------------------


def _now() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def load_resolutions(conn: sqlite3.Connection) -> dict:
    """{movement_id: Resolution} for every movement resolved by hand."""
    rows = conn.execute("SELECT movement_id, status, reason, payment_id FROM resolutions")
    return {movement_id: Resolution(status, reason, payment_id) for movement_id, status, reason, payment_id in rows}


def set_resolution(conn: sqlite3.Connection, movement_id: int, status: str, reason: str = "", payment_id: int = None):
    if status not in STATUS_LABELS:
        raise ValueError(f"estado desconocido: {status}")
    with conn:
        conn.execute(
            "INSERT INTO resolutions (movement_id, status, reason, payment_id, created_at) VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(movement_id) DO UPDATE SET status = excluded.status, reason = excluded.reason, "
            "payment_id = excluded.payment_id, created_at = excluded.created_at",
            (movement_id, status, reason.strip(), payment_id, _now()),
        )


def clear_resolution(conn: sqlite3.Connection, movement_id: int):
    """Undo a manual decision; if it was a grouped payment, every purchase it covered is undone too."""
    with conn:
        conn.execute("DELETE FROM resolutions WHERE movement_id = ? OR payment_id = ?", (movement_id, movement_id))


def accept_group(conn: sqlite3.Connection, payment_id: int, purchase_ids: list):
    """Record that `payment_id` paid all of `purchase_ids` together."""
    reason = "Pago agrupado"
    with conn:
        for purchase_id in purchase_ids:
            conn.execute(
                "INSERT INTO resolutions (movement_id, status, reason, payment_id, created_at) VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT(movement_id) DO UPDATE SET status = excluded.status, reason = excluded.reason, "
                "payment_id = excluded.payment_id, created_at = excluded.created_at",
                (purchase_id, PAID, reason, payment_id, _now()),
            )
        conn.execute("DELETE FROM dismissed_suggestions WHERE payment_id = ?", (payment_id,))


def dismiss_suggestions(conn: sqlite3.Connection, payment_id: int):
    """Stop suggesting groups for this payment."""
    with conn:
        conn.execute(
            "INSERT OR REPLACE INTO dismissed_suggestions (payment_id, created_at) VALUES (?, ?)",
            (payment_id, _now()),
        )


def load_dismissed(conn: sqlite3.Connection) -> set:
    return {payment_id for (payment_id,) in conn.execute("SELECT payment_id FROM dismissed_suggestions")}


# --- Grouped payments -------------------------------------------------------


def _amount(value) -> float:
    return round(float(value), 2)


def find_group_suggestions(
    unpaid: pd.DataFrame,
    orphan_payments: pd.DataFrame,
    max_purchases: int = config.GROUP_MATCH_MAX_PURCHASES,
    tolerance: float = config.GROUP_MATCH_TOLERANCE,
    window_days: int = config.MATCH_WINDOW_DAYS,
    early_tolerance_days: int = config.PAYMENT_EARLY_TOLERANCE_DAYS,
    dismissed: set = frozenset(),
) -> list:
    """
    For each orphan payment, the combinations of 2..max_purchases unpaid purchases
    of the same currency, inside the matching window, that add up to it. They are
    only suggestions: with many purchases some combination adds up to almost any
    amount, so nothing is applied without confirmation.
    """
    suggestions = []
    window = pd.Timedelta(days=window_days)
    early = pd.Timedelta(days=early_tolerance_days)

    for _, payment in orphan_payments.sort_values("Date", kind="stable").iterrows():
        if "Id" in payment and payment["Id"] in dismissed:
            continue
        paid_on = payment["Date"]
        candidates = unpaid[
            (unpaid["Currency"] == payment["Currency"])
            & (unpaid["Date"] >= paid_on - window)
            & (unpaid["Date"] <= paid_on + early)
            & (unpaid["Amount"] > 0)
            & (unpaid["Amount"] <= _amount(payment["Amount"]) + tolerance)
        ]
        # Closest to the payment first
        candidates = candidates.assign(_gap=(paid_on - candidates["Date"]).abs())
        candidates = candidates.sort_values(["_gap", "Date"], kind="stable").head(GROUP_MAX_CANDIDATES)
        records = candidates.drop(columns="_gap").to_dict("records")
        amounts = [_amount(r["Amount"]) for r in records]
        target = _amount(payment["Amount"])

        options = []
        for size in range(2, max_purchases + 1):
            for combo in itertools.combinations(range(len(records)), size):
                if abs(sum(amounts[i] for i in combo) - target) <= tolerance:
                    options.append(sorted((records[i] for i in combo), key=lambda r: r["Date"]))
                    if len(options) >= GROUP_MAX_OPTIONS:
                        break
            if len(options) >= GROUP_MAX_OPTIONS:
                break
        if options:
            suggestions.append(GroupSuggestion(payment=payment.to_dict(), options=options))
    return suggestions
