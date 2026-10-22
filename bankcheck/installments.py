"""
Purchases in installments (proposal 12): what is still owed and until when.

Each charge of an installment purchase shows up as its own movement with
"Installments" like "03/12" and the value of one installment as its amount.
The latest charge seen of each purchase tells how many are left.
"""
import re

import pandas as pd

from bankcheck.matching import is_payment_description

INSTALLMENT_RE = re.compile(r"^\s*(\d+)\s*/\s*(\d+)\s*$")

PLAN_COLUMNS = [
    "Currency", "Description", "Amount", "Current", "Total", "Remaining", "Remaining Debt", "Last Charge", "Ends",
]


def parse_installments(value):
    """"03/12" -> (3, 12); None when it isn't an installment number."""
    match = INSTALLMENT_RE.match(value) if isinstance(value, str) else None
    if not match:
        return None
    current, total = int(match.group(1)), int(match.group(2))
    return (current, total) if 0 < current <= total else None


def installment_plans(movements: pd.DataFrame, include_finished: bool = False) -> pd.DataFrame:
    """
    One row per purchase in more than one installment, with the installment
    value ("Amount"), "Current"/"Total", "Remaining", "Remaining Debt" and the
    month the last installment is due ("Ends").
    """
    parsed = movements["Installments"].map(parse_installments)
    is_plan = parsed.map(lambda p: p is not None and p[1] > 1) & ~movements["Description"].map(
        is_payment_description
    ).astype(bool)
    df = movements[is_plan].copy()
    if df.empty:
        return pd.DataFrame(columns=PLAN_COLUMNS)

    df["Current"] = parsed[is_plan].map(lambda p: p[0])
    df["Total"] = parsed[is_plan].map(lambda p: p[1])
    # The month the charge belongs to: when it was seen in the bank's view if
    # known (the view shows the current period), else the movement's date
    reference = df["Last Seen"] if "Last Seen" in df else df["Date"]
    df["Month"] = pd.to_datetime(reference).dt.to_period("M")

    latest = (
        df.sort_values(["Current", "Date"], kind="stable")
        .groupby(["Currency", "Description", "Amount", "Total"], sort=False)
        .tail(1)
    )
    latest = latest.assign(
        Remaining=latest["Total"] - latest["Current"],
        **{"Last Charge": latest["Date"]},
    )
    latest["Remaining Debt"] = latest["Remaining"] * latest["Amount"]
    latest["Ends"] = [month + int(remaining) for month, remaining in zip(latest["Month"], latest["Remaining"])]
    if not include_finished:
        latest = latest[latest["Remaining"] > 0]
    return latest[PLAN_COLUMNS].sort_values(["Ends", "Description"], kind="stable").reset_index(drop=True)


def summary(plans: pd.DataFrame) -> dict:
    """{currency: (monthly commitment, total remaining debt)} of the active plans."""
    return {
        currency: (group["Amount"].sum(), group["Remaining Debt"].sum())
        for currency, group in plans.groupby("Currency", sort=True)
    }


def projection(plans: pd.DataFrame, currency: str = "CLP", months: int = 12) -> pd.DataFrame:
    """
    What the installments will charge in each of the next `months` months
    ("Month", "Amount"), from the month after each plan's last charge seen.
    """
    df = plans[plans["Currency"] == currency]
    if df.empty:
        return pd.DataFrame(columns=["Month", "Amount"])
    start = min(end - int(rem) for end, rem in zip(df["Ends"], df["Remaining"])) + 1
    rows = []
    for k in range(months):
        month = start + k
        due = sum(
            amount for amount, end, rem in zip(df["Amount"], df["Ends"], df["Remaining"])
            if end - int(rem) < month <= end
        )
        rows.append({"Month": month, "Amount": due})
    return pd.DataFrame(rows)
