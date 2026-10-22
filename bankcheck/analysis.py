"""Find unpaid purchases, per currency."""
from dataclasses import dataclass

import pandas as pd

from bankcheck.matching import match_payments, split_movements


@dataclass
class CurrencyAnalysis:
    currency: str
    unpaid: pd.DataFrame
    matches: pd.DataFrame
    orphan_payments: pd.DataFrame
    total_unpaid: float
    total_payments: float
    total_purchases: float

    @property
    def difference(self) -> float:
        return self.total_payments - self.total_purchases


def analyze(movements: pd.DataFrame, start_date=None) -> list:
    """
    Match purchases and payments of each currency separately and return one
    CurrencyAnalysis per currency present. Movements before `start_date` are ignored.
    """
    df = movements.reset_index(drop=True)
    if start_date is not None:
        df = df[df["Date"] >= pd.Timestamp(start_date)]

    results = []
    for currency, group in df.groupby("Currency", sort=True):
        purchases, payments = split_movements(group)
        result = match_payments(purchases, payments)
        results.append(
            CurrencyAnalysis(
                currency=currency,
                unpaid=result.unpaid,
                matches=result.matches,
                orphan_payments=result.orphan_payments,
                total_unpaid=result.unpaid["Amount"].sum(),
                total_payments=payments["Amount"].sum(),
                total_purchases=purchases["Amount"].sum(),
            )
        )
    return results
