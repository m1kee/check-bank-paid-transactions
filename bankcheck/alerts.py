"""
Charges worth a second look (proposal 16): possible duplicates, unusual
amounts, and merchants or cities never seen before.

Only movements from the last config.ALERT_LOOKBACK_DAYS (counted back from the
newest movement, so an old export still gets its alerts) raise alerts.
"""
from dataclasses import dataclass, field

import pandas as pd

from bankcheck import config
from bankcheck.matching import is_payment_description
from bankcheck.text import merchant_key, normalize

DUPLICATE = "duplicate"
UNUSUAL = "unusual"
NEW_MERCHANT = "new_merchant"
NEW_CITY = "new_city"

KIND_LABELS = {
    DUPLICATE: "Posible cobro duplicado",
    UNUSUAL: "Monto inusual",
    NEW_MERCHANT: "Comercio nuevo",
    NEW_CITY: "Ciudad nueva",
}

# "New" merchants and cities: first seen in the last days of the lookback
NEW_RECENT_DAYS = 30


@dataclass
class Alert:
    kind: str
    detail: str
    movements: list = field(default_factory=list)  # rows (dicts)

    @property
    def label(self) -> str:
        return KIND_LABELS[self.kind]

    @property
    def date(self):
        return max(m["Date"] for m in self.movements)


def _purchases(movements: pd.DataFrame) -> pd.DataFrame:
    is_payment = movements["Description"].map(is_payment_description).astype(bool)
    return movements[~is_payment & (movements["Amount"] > 0)]


def _duplicates(df: pd.DataFrame, since) -> list:
    alerts = []
    max_gap = config.DUPLICATE_MAX_DAYS
    for _, group in df.groupby(["Currency", "Description", "Amount"], sort=False):
        if len(group) < 2:
            continue
        rows = group.sort_values("Date", kind="stable").to_dict("records")
        for earlier, later in zip(rows, rows[1:]):
            gap = (later["Date"] - earlier["Date"]).days
            if gap <= max_gap and later["Date"] >= since:
                when = "el mismo día" if gap == 0 else f"con {gap} {'día' if gap == 1 else 'días'} de diferencia"
                alerts.append(Alert(DUPLICATE, f"Mismo comercio y monto {when}.", [earlier, later]))
    return alerts


def _unusual_amounts(df: pd.DataFrame, since) -> list:
    alerts = []
    single = df[df["Installments"].isin(["01/01", ""])]
    single = single.assign(Merchant=single["Description"].map(merchant_key))
    for _, group in single.groupby(["Currency", "Merchant"], sort=False):
        group = group.sort_values("Date", kind="stable")
        amounts = list(group["Amount"])
        for i, row in enumerate(group.to_dict("records")):
            previous = amounts[:i]
            if row["Date"] < since or len(previous) < config.UNUSUAL_MIN_HISTORY:
                continue
            median = pd.Series(previous).median()
            if median > 0 and row["Amount"] > config.UNUSUAL_AMOUNT_FACTOR * median:
                alerts.append(
                    Alert(UNUSUAL, f"{row['Amount'] / median:.1f} veces lo habitual en este comercio.", [row])
                )
    return alerts


def _first_seen(df: pd.DataFrame, key: pd.Series, newest, kind: str, detail: str) -> list:
    """An alert for each key whose first movement is recent, when the history is long enough to tell."""
    if df.empty or (newest - df["Date"].min()).days < config.NEW_MERCHANT_MIN_HISTORY_DAYS:
        return []
    recent = newest - pd.Timedelta(days=NEW_RECENT_DAYS)
    firsts = df.assign(_key=key).sort_values("Date", kind="stable").drop_duplicates("_key")
    firsts = firsts[(firsts["_key"] != "") & (firsts["Date"] >= recent)]
    return [Alert(kind, detail, [row]) for row in firsts.drop(columns="_key").to_dict("records")]


def find_alerts(movements: pd.DataFrame) -> list:
    """Every alert, newest first."""
    df = _purchases(movements)
    if df.empty:
        return []
    newest = movements["Date"].max()
    since = newest - pd.Timedelta(days=config.ALERT_LOOKBACK_DAYS)

    alerts = _duplicates(df, since) + _unusual_amounts(df, since)
    alerts += _first_seen(df, df["Currency"] + "|" + df["Description"].map(merchant_key), newest,
                          NEW_MERCHANT, "Primera compra en este comercio.")
    alerts += _first_seen(df, df["City"].map(normalize), newest, NEW_CITY, "Primera compra en esta ciudad.")
    return sorted(alerts, key=lambda a: a.date, reverse=True)
