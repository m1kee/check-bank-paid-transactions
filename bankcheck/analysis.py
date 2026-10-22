"""Find unpaid purchases, per currency."""
from dataclasses import dataclass, field

import pandas as pd

from bankcheck.matching import match_payments, split_movements
from bankcheck.reconcile import IGNORED, find_group_suggestions


@dataclass
class CurrencyAnalysis:
    currency: str
    unpaid: pd.DataFrame
    matches: pd.DataFrame  # purchases paid automatically, with their payment (04)
    orphan_payments: pd.DataFrame
    total_unpaid: float
    total_payments: float
    total_purchases: float
    # Purchases resolved by hand (03, 11), with "Status", "Reason" and the covering payment
    resolved: pd.DataFrame = None
    ignored_payments: pd.DataFrame = None
    suggestions: list = field(default_factory=list)  # grouped payments to confirm (11)

    @property
    def difference(self) -> float:
        return self.total_payments - self.total_purchases


def filter_dates(movements: pd.DataFrame, start_date=None, end_date=None) -> pd.DataFrame:
    """Movements between `start_date` and `end_date`, both inclusive (either may be None)."""
    df = movements
    if start_date is not None:
        df = df[df["Date"] >= pd.Timestamp(start_date)]
    if end_date is not None:
        df = df[df["Date"] <= pd.Timestamp(end_date)]
    return df


def _empty_like(df: pd.DataFrame, *extra) -> pd.DataFrame:
    return df.iloc[0:0].assign(**{name: pd.Series(dtype="object") for name in extra})


def _apply_resolutions(purchases, payments, resolutions: dict, by_id: dict):
    """Split out what was decided by hand. Returns (open purchases, open payments, resolved, ignored payments)."""
    if not resolutions or "Id" not in purchases:
        return purchases, payments, _empty_like(purchases, "Status", "Reason", "Payment Description"), _empty_like(payments)

    is_resolved = purchases["Id"].isin(resolutions.keys())
    resolved = purchases[is_resolved].copy()
    found = [resolutions[i] for i in resolved["Id"]]
    resolved["Status"] = [r.status for r in found]
    resolved["Reason"] = [r.reason for r in found]
    resolved["Payment Description"] = [
        by_id.get(r.payment_id, {}).get("Description", "") if r.payment_id else "" for r in found
    ]

    used_payments = {r.payment_id for r in resolutions.values() if r.payment_id}
    ignored_ids = {i for i, r in resolutions.items() if r.status == IGNORED}
    is_ignored = payments["Id"].isin(ignored_ids)
    open_payments = payments[~is_ignored & ~payments["Id"].isin(used_payments)]
    return purchases[~is_resolved], open_payments, resolved, payments[is_ignored]


def analyze(
    movements: pd.DataFrame,
    start_date=None,
    end_date=None,
    resolutions: dict = None,
    dismissed: set = frozenset(),
) -> list:
    """
    Match purchases and payments of each currency separately and return one
    CurrencyAnalysis per currency present. Only movements between `start_date`
    and `end_date` are used. `resolutions` ({movement id: Resolution}, see
    reconcile.py) takes the movements decided by hand out of the matching.
    """
    df = filter_dates(movements.reset_index(drop=True), start_date, end_date)
    # The covering payment may fall outside the date range
    by_id = movements.set_index("Id").to_dict("index") if "Id" in movements else {}

    results = []
    for currency, group in df.groupby("Currency", sort=True):
        purchases, payments = split_movements(group)
        open_purchases, open_payments, resolved, ignored_payments = _apply_resolutions(
            purchases, payments, resolutions, by_id
        )
        result = match_payments(open_purchases, open_payments)
        counted_purchases = purchases[~purchases.index.isin(resolved[resolved["Status"] == IGNORED].index)]
        results.append(
            CurrencyAnalysis(
                currency=currency,
                unpaid=result.unpaid,
                matches=result.matches,
                orphan_payments=result.orphan_payments,
                total_unpaid=result.unpaid["Amount"].sum(),
                total_payments=payments.drop(index=ignored_payments.index)["Amount"].sum(),
                total_purchases=counted_purchases["Amount"].sum(),
                resolved=resolved,
                ignored_payments=ignored_payments,
                suggestions=find_group_suggestions(result.unpaid, result.orphan_payments, dismissed=dismissed),
            )
        )
    return results
