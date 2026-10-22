"""
Subscriptions and other recurring charges (proposal 15).

A merchant is recurring when its latest charges come about every month
(config.SUBSCRIPTION_INTERVAL_DAYS apart), in at least SUBSCRIPTION_MIN_MONTHS
different months, for a similar amount. The newest charge may differ in
amount: that is how a price increase shows up.
"""
from dataclasses import dataclass

import pandas as pd

from bankcheck import config
from bankcheck.matching import is_payment_description
from bankcheck.text import merchant_key

# A subscription whose last charge is older than this (relative to the newest
# movement) is considered cancelled
ACTIVE_MAX_DAYS = 45


@dataclass(frozen=True)
class Subscription:
    currency: str
    description: str  # as in the latest charge
    amount: float  # latest charge
    previous_amount: float
    charges: int
    first_date: pd.Timestamp
    last_date: pd.Timestamp
    amounts: tuple = ()  # every charge of the run, oldest first

    @property
    def annual_cost(self) -> float:
        return self.amount * 12

    @property
    def price_change(self) -> float:
        return self.amount - self.previous_amount

    @property
    def price_increased(self) -> bool:
        return self.price_change > 0

    @property
    def next_charge(self) -> pd.Timestamp:
        return self.last_date + pd.DateOffset(months=1)


def _single_charges(movements: pd.DataFrame) -> pd.DataFrame:
    is_payment = movements["Description"].map(is_payment_description).astype(bool)
    single = movements["Installments"].isin(["01/01", ""])
    return movements[~is_payment & single & (movements["Amount"] > 0)]


def _recurring_run(charges: pd.DataFrame) -> pd.DataFrame:
    """The latest charges that come every ~month, newest last (may be shorter than 2)."""
    low, high = config.SUBSCRIPTION_INTERVAL_DAYS
    dates = list(charges["Date"])
    start = len(dates) - 1
    while start > 0 and low <= (dates[start] - dates[start - 1]).days <= high:
        start -= 1
    return charges.iloc[start:]


def _similar_amounts(run: pd.DataFrame) -> bool:
    """Every charge but the newest within the tolerance of their median."""
    earlier = run["Amount"].iloc[:-1]
    median = earlier.median()
    return bool(((earlier - median).abs() <= median * config.SUBSCRIPTION_AMOUNT_TOLERANCE).all())


def detect_subscriptions(movements: pd.DataFrame, include_cancelled: bool = False) -> list:
    """The recurring charges in `movements`, highest annual cost first."""
    charges = _single_charges(movements)
    if charges.empty:
        return []
    newest = movements["Date"].max()
    charges = charges.assign(Merchant=charges["Description"].map(merchant_key))

    found = []
    for (currency, _), group in charges.groupby(["Currency", "Merchant"], sort=False):
        run = _recurring_run(group.sort_values("Date", kind="stable"))
        months = run["Date"].dt.to_period("M").nunique()
        if months < config.SUBSCRIPTION_MIN_MONTHS or not _similar_amounts(run):
            continue
        last = run.iloc[-1]
        if not include_cancelled and (newest - last["Date"]).days > ACTIVE_MAX_DAYS:
            continue
        found.append(
            Subscription(
                currency=currency,
                description=last["Description"],
                amount=float(last["Amount"]),
                previous_amount=float(run.iloc[-2]["Amount"]),
                charges=len(run),
                first_date=run.iloc[0]["Date"],
                last_date=last["Date"],
                amounts=tuple(float(a) for a in run["Amount"]),
            )
        )
    return sorted(found, key=lambda s: (s.currency, -s.annual_cost, s.description))
