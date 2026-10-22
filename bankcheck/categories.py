"""
Spending categories (proposal 13) and monthly budgets (proposal 30).

A movement's category comes from, in order: a category chosen by hand for that
movement, or the longest rule fragment contained in its description. Payments
to the card are not spending and get their own fixed category.
"""
import calendar
import datetime
import sqlite3
from dataclasses import dataclass

import pandas as pd

from bankcheck import config
from bankcheck.matching import is_payment_description
from bankcheck.text import merchant_key, normalize

UNCATEGORIZED = "Sin categoría"
PAYMENTS = "Pagos de tarjeta"

# Share of the budget from which a category is flagged
BUDGET_WARNING_RATIO = 0.8


class CategoryError(ValueError):
    """An invalid change to categories or rules (shown to the user as is)."""


@dataclass(frozen=True)
class Rule:
    pattern: str
    category: str
    id: int = None


@dataclass(frozen=True)
class Category:
    id: int
    name: str
    budget: float = None
    rule_count: int = 0


@dataclass(frozen=True)
class BudgetLine:
    category: str
    spent: float
    budget: float
    month_ratio: float  # how much of the month has passed, 0..1

    @property
    def ratio(self) -> float:
        return self.spent / self.budget if self.budget else 0.0

    @property
    def status(self) -> str:
        """"over" (spent it all), "warning" (>= 80% or ahead of the month's pace) or "ok"."""
        if self.ratio >= 1:
            return "over"
        if self.ratio >= BUDGET_WARNING_RATIO or self.ratio > self.month_ratio:
            return "warning"
        return "ok"


# --- Assigning categories ----------------------------------------------------


def default_rules() -> list:
    return [Rule(pattern.upper(), name) for name, patterns in config.DEFAULT_CATEGORIES.items() for pattern in patterns]


def _sorted_rules(rules: list) -> list:
    # The longest fragment wins: "UBER EATS" before "UBER"
    return sorted(((normalize(r.pattern), r.category) for r in rules if normalize(r.pattern)),
                  key=lambda pair: (-len(pair[0]), pair[0]))


def categorize(movements: pd.DataFrame, rules: list, overrides: dict = None) -> pd.Series:
    """The category of each movement (same index). `overrides`: {movement id: category name}."""
    ordered = _sorted_rules(rules)
    cache = {}

    def by_rules(description):
        text = normalize(description)
        if text not in cache:
            cache[text] = next((c for pattern, c in ordered if pattern in text), UNCATEGORIZED)
        return cache[text]

    categories = movements["Description"].map(by_rules)
    categories[movements["Description"].map(is_payment_description).astype(bool)] = PAYMENTS
    if overrides and "Id" in movements:
        chosen = movements["Id"].map(overrides)
        categories = chosen.where(chosen.notna(), categories)
    return categories.astype(str)


def with_categories(movements: pd.DataFrame, rules: list, overrides: dict = None) -> pd.DataFrame:
    return movements.assign(Category=categorize(movements, rules, overrides))


# --- Spending ------------------------------------------------------------------


def spending(categorized: pd.DataFrame, month: pd.Period = None, currency: str = "CLP") -> pd.DataFrame:
    """
    Total spent per category (payments excluded; refunds subtract) in `month`,
    with "Amount" and "Count", largest first.
    """
    df = categorized[(categorized["Currency"] == currency) & (categorized["Category"] != PAYMENTS)]
    if month is not None:
        df = df[df["Date"].dt.to_period("M") == month]
    totals = df.groupby("Category").agg(Amount=("Amount", "sum"), Count=("Amount", "size")).reset_index()
    return totals.sort_values(["Amount", "Category"], ascending=[False, True], kind="stable").reset_index(drop=True)


def daily_spending(categorized: pd.DataFrame, month: pd.Period, currency: str = "CLP") -> pd.DataFrame:
    """Spending of every day of `month` ("Date", "Amount"), zero on days without purchases."""
    df = categorized[(categorized["Currency"] == currency) & (categorized["Category"] != PAYMENTS)]
    df = df[df["Date"].dt.to_period("M") == month]
    days = pd.date_range(month.start_time, month.end_time.normalize(), freq="D")
    totals = df.groupby("Date")["Amount"].sum().reindex(days, fill_value=0)
    return pd.DataFrame({"Date": days, "Amount": totals.values})


def monthly_spending(categorized: pd.DataFrame, end: pd.Period, months: int = 12, currency: str = "CLP") -> pd.DataFrame:
    """Total spent in each of the `months` months up to `end` ("Month", "Amount"), zero where nothing was spent."""
    df = categorized[(categorized["Currency"] == currency) & (categorized["Category"] != PAYMENTS)]
    totals = df.groupby(df["Date"].dt.to_period("M"))["Amount"].sum()
    periods = [end - k for k in range(months - 1, -1, -1)]
    return pd.DataFrame({"Month": periods, "Amount": [float(totals.get(p, 0)) for p in periods]})


def category_history(categorized: pd.DataFrame, end: pd.Period, months: int = 6, currency: str = "CLP") -> dict:
    """{category: [amount per month]} for the `months` months up to `end`, oldest first."""
    df = categorized[(categorized["Currency"] == currency) & (categorized["Category"] != PAYMENTS)]
    periods = [end - k for k in range(months - 1, -1, -1)]
    table = df.groupby([df["Category"], df["Date"].dt.to_period("M")])["Amount"].sum()
    return {
        category: [float(table.get((category, p), 0)) for p in periods]
        for category in df["Category"].unique()
    }


def uncategorized_summary(categorized: pd.DataFrame, limit: int = 30) -> pd.DataFrame:
    """The merchants without a category, most frequent first, to add rules for them."""
    df = categorized[categorized["Category"] == UNCATEGORIZED]
    if df.empty:
        return pd.DataFrame(columns=["Merchant", "Example", "Count", "Amount", "Currency"])
    df = df.assign(Merchant=df["Description"].map(merchant_key))
    summary = df.groupby(["Merchant", "Currency"]).agg(
        Example=("Description", "last"), Count=("Amount", "size"), Amount=("Amount", "sum")
    ).reset_index()
    return summary.sort_values(["Count", "Amount"], ascending=False, kind="stable").head(limit).reset_index(drop=True)


def month_ratio(month: pd.Period, today: datetime.date = None) -> float:
    """How much of `month` has passed on `today`: 1 for past months, 0 for future ones."""
    today = today or datetime.date.today()
    current = pd.Period(today, freq="M")
    if month < current:
        return 1.0
    if month > current:
        return 0.0
    return today.day / calendar.monthrange(today.year, today.month)[1]


def budget_lines(categories: list, month_spending: pd.DataFrame, month: pd.Period, today=None) -> list:
    """One BudgetLine per category with a budget (CLP)."""
    spent = dict(zip(month_spending["Category"], month_spending["Amount"]))
    ratio = month_ratio(month, today)
    return [
        BudgetLine(c.name, float(spent.get(c.name, 0)), float(c.budget), ratio)
        for c in categories
        if c.budget
    ]


# --- Persistence ---------------------------------------------------------------


def list_categories(conn: sqlite3.Connection) -> list:
    rows = conn.execute(
        "SELECT c.id, c.name, c.budget, COUNT(r.id) FROM categories c "
        "LEFT JOIN category_rules r ON r.category_id = c.id GROUP BY c.id ORDER BY c.name COLLATE NOCASE"
    )
    return [Category(id, name, budget, count) for id, name, budget, count in rows]


def load_rules(conn: sqlite3.Connection) -> list:
    rows = conn.execute(
        "SELECT r.id, r.pattern, c.name FROM category_rules r JOIN categories c ON c.id = r.category_id "
        "ORDER BY c.name COLLATE NOCASE, r.pattern"
    )
    return [Rule(pattern, name, id) for id, pattern, name in rows]


def load_overrides(conn: sqlite3.Connection) -> dict:
    rows = conn.execute(
        "SELECT m.id, c.name FROM movements m JOIN categories c ON c.id = m.category_id"
    )
    return dict(rows.fetchall())


def _clean_name(name: str) -> str:
    name = " ".join((name or "").split())
    if not name:
        raise CategoryError("El nombre de la categoría no puede quedar vacío.")
    if name.casefold() in (UNCATEGORIZED.casefold(), PAYMENTS.casefold()):
        raise CategoryError(f"'{name}' es una categoría reservada.")
    return name


def _clean_budget(budget):
    if budget in (None, ""):
        return None
    try:
        value = float(str(budget).replace(".", "").replace(",", ".").replace("$", "").strip())
    except ValueError:
        raise CategoryError(f"Presupuesto inválido: '{budget}'.")
    if value < 0:
        raise CategoryError("El presupuesto no puede ser negativo.")
    return value or None


def create_category(conn: sqlite3.Connection, name: str, budget=None) -> int:
    name = _clean_name(name)
    try:
        with conn:
            return conn.execute(
                "INSERT INTO categories (name, budget) VALUES (?, ?)", (name, _clean_budget(budget))
            ).lastrowid
    except sqlite3.IntegrityError:
        raise CategoryError(f"Ya existe la categoría '{name}'.")


def rename_category(conn: sqlite3.Connection, category_id: int, name: str):
    name = _clean_name(name)
    try:
        with conn:
            conn.execute("UPDATE categories SET name = ? WHERE id = ?", (name, category_id))
    except sqlite3.IntegrityError:
        raise CategoryError(f"Ya existe la categoría '{name}'. Para juntarlas, usa \"Unir\".")


def set_budget(conn: sqlite3.Connection, category_id: int, budget):
    with conn:
        conn.execute("UPDATE categories SET budget = ? WHERE id = ?", (_clean_budget(budget), category_id))


def delete_category(conn: sqlite3.Connection, category_id: int):
    """Its rules go away and its movements go back to being categorized by the remaining rules."""
    with conn:
        conn.execute("DELETE FROM categories WHERE id = ?", (category_id,))


def merge_categories(conn: sqlite3.Connection, source_id: int, target_id: int):
    """Move the rules and movements of `source_id` into `target_id` and delete `source_id`."""
    if source_id == target_id:
        raise CategoryError("Elige dos categorías distintas para unir.")
    with conn:
        conn.execute("UPDATE category_rules SET category_id = ? WHERE category_id = ?", (target_id, source_id))
        conn.execute("UPDATE movements SET category_id = ? WHERE category_id = ?", (target_id, source_id))
        conn.execute("DELETE FROM categories WHERE id = ?", (source_id,))


def add_rule(conn: sqlite3.Connection, pattern: str, category_id: int):
    """Add a rule; if the fragment already had one, it now points to `category_id`."""
    pattern = " ".join((pattern or "").split()).upper()
    if len(pattern) < 3:
        raise CategoryError("La regla necesita al menos 3 caracteres.")
    with conn:
        conn.execute(
            "INSERT INTO category_rules (pattern, category_id, created_at) VALUES (?, ?, datetime('now')) "
            "ON CONFLICT(pattern) DO UPDATE SET category_id = excluded.category_id",
            (pattern, category_id),
        )


def delete_rule(conn: sqlite3.Connection, rule_id: int):
    with conn:
        conn.execute("DELETE FROM category_rules WHERE id = ?", (rule_id,))


def set_movement_category(conn: sqlite3.Connection, movement_id: int, category_id: int = None):
    """Choose the category of one movement by hand (None: back to the rules)."""
    with conn:
        conn.execute("UPDATE movements SET category_id = ? WHERE id = ?", (category_id, movement_id))
