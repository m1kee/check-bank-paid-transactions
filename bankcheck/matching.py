"""Pair purchases with the payments that covered them."""
from collections import defaultdict
from dataclasses import dataclass

import pandas as pd

from bankcheck import config


@dataclass
class MatchResult:
    matches: pd.DataFrame  # one row per purchase, with the payment that covered it
    unpaid: pd.DataFrame
    orphan_payments: pd.DataFrame  # payments that didn't cover any purchase


def is_payment_description(description: str) -> bool:
    """Return True when the description matches known payment patterns."""
    if not isinstance(description, str):
        return False

    desc = description.upper().strip()
    if not desc:
        return False

    if any(exclusion.upper() in desc for exclusion in config.PAYMENT_EXCLUSIONS):
        return False

    return any(term.upper() in desc for term in config.PAYMENT_TERMS)


def split_movements(movements: pd.DataFrame):
    """Return (purchases, payments); payment amounts are made positive."""
    # astype(bool): on an empty frame apply() returns an object Series, which
    # pandas would treat as a column selection instead of a mask
    is_payment = movements["Description"].apply(is_payment_description).astype(bool)

    payments = movements[is_payment].copy()
    payments["Amount"] = payments["Amount"].abs()

    is_purchase = (~is_payment) & (movements["Installments"] == config.PURCHASE_INSTALLMENT_CONDITION)
    purchases = movements[is_purchase].copy()
    return purchases, payments


def _amount_key(row) -> tuple:
    return (row["Currency"], round(float(row["Amount"]), 2))


def _take_purchase(candidates: list, paid_on, window, tolerance):
    """Remove and return the oldest purchase in `candidates` that a payment made on `paid_on` can cover."""
    for pos, (bought_on, purchase_idx) in enumerate(candidates):
        if bought_on < paid_on - window:
            continue
        if bought_on > paid_on + tolerance:
            return None
        del candidates[pos]
        return purchase_idx
    return None


def match_payments(
    purchases: pd.DataFrame,
    payments: pd.DataFrame,
    window_days: int = config.MATCH_WINDOW_DAYS,
    early_tolerance_days: int = config.PAYMENT_EARLY_TOLERANCE_DAYS,
) -> MatchResult:
    """
    Pair each payment with the oldest unpaid purchase of the same amount and currency
    that it can cover: bought at most `window_days` before the payment, or at most
    `early_tolerance_days` after it. Payments are processed in date order, so a payment
    never covers a purchase it predates and repeated amounts are paid oldest first.
    """
    window = pd.Timedelta(days=window_days)
    tolerance = pd.Timedelta(days=early_tolerance_days)

    open_purchases = defaultdict(list)
    for idx, row in purchases.sort_values("Date", kind="stable").iterrows():
        open_purchases[_amount_key(row)].append((row["Date"], idx))

    pairs = []
    orphan_idx = []
    for pay_idx, payment in payments.sort_values("Date", kind="stable").iterrows():
        candidates = open_purchases.get(_amount_key(payment), [])
        purchase_idx = _take_purchase(candidates, payment["Date"], window, tolerance)
        if purchase_idx is None:
            orphan_idx.append(pay_idx)
        else:
            pairs.append((purchase_idx, pay_idx))

    return _result(purchases, payments, pairs, orphan_idx)


def match_statement_payments(
    purchases: pd.DataFrame,
    payments: pd.DataFrame,
    tolerance: float = config.STATEMENT_MATCH_TOLERANCE,
    early_tolerance_days: int = config.PAYMENT_EARLY_TOLERANCE_DAYS,
) -> MatchResult:
    """
    For cards paid by statement balance (each payment is the whole billed
    amount): a payment covers the run of consecutive unpaid purchases, in date
    order and made before it, that adds up to it. The earliest such run wins;
    purchases before it (e.g. from a cycle only partly in the history) stay unpaid.
    A payment with no exact run (a partial payment) is left as an orphan.
    """
    tolerance_days = pd.Timedelta(days=early_tolerance_days)
    open_purchases = list(purchases.sort_values("Date", kind="stable").iterrows())

    pairs = []
    orphan_idx = []
    for pay_idx, payment in payments.sort_values("Date", kind="stable").iterrows():
        candidates = [(idx, row) for idx, row in open_purchases if row["Date"] <= payment["Date"] + tolerance_days]
        amounts = [float(row["Amount"]) for _, row in candidates]
        target = float(payment["Amount"])
        # With refunds (negative amounts) a run can come back down, so it can't stop early
        can_stop_early = all(a >= 0 for a in amounts)
        run = None
        for start in range(len(amounts)):
            total = 0.0
            for end in range(start, len(amounts)):
                total += amounts[end]
                if abs(total - target) <= tolerance:
                    run = (start, end)
                    break
                if can_stop_early and total > target + tolerance:
                    break
            if run:
                break
        if run is None:
            orphan_idx.append(pay_idx)
            continue
        covered = {idx for idx, _ in candidates[run[0]:run[1] + 1]}
        pairs.extend((idx, pay_idx) for idx in sorted(covered, key=lambda i: purchases.at[i, "Date"]))
        open_purchases = [(idx, row) for idx, row in open_purchases if idx not in covered]

    return _result(purchases, payments, pairs, orphan_idx)


def _result(purchases, payments, pairs: list, orphan_idx: list) -> MatchResult:
    """Build the MatchResult from (purchase index, payment index) pairs."""
    matched_purchases = purchases.loc[[p for p, _ in pairs]]
    matched_payments = payments.loc[[q for _, q in pairs]]
    matches = matched_purchases.assign(
        **{
            "Payment Date": pd.to_datetime(matched_payments["Date"].values),
            "Payment Description": matched_payments["Description"].values,
        }
    )
    matches["Days To Pay"] = (matches["Payment Date"] - pd.to_datetime(matches["Date"])).dt.days

    return MatchResult(
        matches=matches.sort_values("Date", kind="stable"),
        unpaid=purchases.drop(index=matched_purchases.index).sort_values("Date", kind="stable"),
        orphan_payments=payments.loc[orphan_idx].sort_values("Date", kind="stable"),
    )
