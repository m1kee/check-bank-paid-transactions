"""
Everything about where the money goes, computed once for the web app's home
page and for the CLI's HTML report: spending by category and by day (13, 14),
budgets (30), installments (12), subscriptions (15) and alerts (16).
"""
import datetime
from dataclasses import dataclass, field

import pandas as pd

from bankcheck import alerts as alerts_module
from bankcheck import categories as cat
from bankcheck import installments, recurring

AGE_BUCKETS = [("0–7 días", 0, 7), ("8–30 días", 8, 30), ("Más de 30 días", 31, None)]


@dataclass
class Insights:
    month: pd.Period
    currency: str
    categorized: pd.DataFrame
    spending: pd.DataFrame  # "Category", "Amount", "Count", "Previous" (previous month)
    daily: pd.DataFrame  # "Date", "Amount"
    monthly: pd.DataFrame = None  # "Month", "Amount": the 12 months up to `month`
    pace: list = field(default_factory=list)  # cumulative spending per day of `month`; None for days still to come
    previous_pace: list = field(default_factory=list)  # the same for the previous month
    budgets: list = field(default_factory=list)
    plans: pd.DataFrame = None
    plans_summary: dict = field(default_factory=dict)
    projection: pd.DataFrame = None
    subscriptions: list = field(default_factory=list)
    alerts: list = field(default_factory=list)

    @property
    def total_spent(self) -> float:
        return float(self.spending["Amount"].sum())

    @property
    def previous_spent(self) -> float:
        return float(self.spending["Previous"].sum())


def latest_month(movements: pd.DataFrame) -> pd.Period:
    """The month of the newest movement (so an old export still shows its data), or the current one."""
    if movements.empty:
        return pd.Period(datetime.date.today(), freq="M")
    return movements["Date"].max().to_period("M")


def build_insights(
    movements: pd.DataFrame,
    rules: list,
    overrides: dict = None,
    categories: list = None,
    month: pd.Period = None,
    currency: str = "CLP",
    today: datetime.date = None,
    dismissed_alerts: set = frozenset(),
) -> Insights:
    month = month or latest_month(movements)
    categorized = cat.with_categories(movements, rules, overrides)

    current = cat.spending(categorized, month, currency)
    previous = cat.spending(categorized, month - 1, currency)
    merged = current.merge(previous[["Category", "Amount"]].rename(columns={"Amount": "Previous"}),
                           on="Category", how="outer").fillna({"Amount": 0, "Count": 0, "Previous": 0})
    merged = merged.sort_values(["Amount", "Previous"], ascending=False, kind="stable").reset_index(drop=True)

    plans = installments.installment_plans(movements)
    daily = cat.daily_spending(categorized, month, currency)
    previous_daily = cat.daily_spending(categorized, month - 1, currency)
    today = pd.Timestamp(today or datetime.date.today())
    pace = [float(v) for v in daily["Amount"].cumsum()]
    if month == today.to_period("M"):
        pace = [v if day <= today.day else None for day, v in enumerate(pace, start=1)]
    return Insights(
        month=month,
        currency=currency,
        categorized=categorized,
        spending=merged,
        daily=daily,
        monthly=cat.monthly_spending(categorized, month, 12, currency),
        pace=pace,
        previous_pace=[float(v) for v in previous_daily["Amount"].cumsum()],
        budgets=cat.budget_lines(categories or [], current, month, today) if currency == "CLP" else [],
        plans=plans,
        plans_summary=installments.summary(plans),
        projection=installments.projection(plans, currency),
        subscriptions=recurring.detect_subscriptions(movements),
        alerts=alerts_module.find_alerts(movements, dismissed_alerts),
    )


def pending_by_age(result, today: datetime.date = None) -> list:
    """(bucket label, unpaid amount) for one CurrencyAnalysis: how long purchases have been waiting."""
    today = pd.Timestamp(today or datetime.date.today())
    age = (today - result.unpaid["Date"]).dt.days
    rows = []
    for label, low, high in AGE_BUCKETS:
        in_bucket = (age >= low) & ((age <= high) if high is not None else True)
        rows.append((label, float(result.unpaid.loc[in_bucket, "Amount"].sum())))
    return rows


MONTH_NAMES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
               "septiembre", "octubre", "noviembre", "diciembre"]


def month_name(month: pd.Period, short: bool = False) -> str:
    name = MONTH_NAMES[month.month - 1]
    return f"{name[:3]} {month.year % 100:02d}" if short else f"{name} {month.year}"
