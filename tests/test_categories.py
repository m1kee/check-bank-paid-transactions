import datetime
import unittest

import pandas as pd

from bankcheck import categories as cat
from bankcheck import history
from tests.helpers import movements

RULES = [cat.Rule("UBER", "Transporte"), cat.Rule("UBER EATS", "Delivery"), cat.Rule("LIDER", "Supermercado")]


class CategorizeTests(unittest.TestCase):
    def test_every_movement_gets_a_category(self):
        df = movements(
            [
                ("2026-10-01", "UBER TRIP", 4500),
                ("2026-10-02", "UBER EATS PEDIDO", 9000),
                ("2026-10-03", "Líder Express 123", 23450),
                ("2026-10-04", "TIENDA RARA", 1000),
                ("2026-10-05", "PAGO PESOS TEF", -10000),
            ]
        )
        self.assertEqual(
            cat.categorize(df, RULES).tolist(),
            ["Transporte", "Delivery", "Supermercado", cat.UNCATEGORIZED, cat.PAYMENTS],
        )

    def test_a_category_chosen_by_hand_wins(self):
        df = movements([("2026-10-01", "UBER TRIP", 4500)]).assign(Id=[7])
        self.assertEqual(cat.categorize(df, RULES, {7: "Trabajo"}).tolist(), ["Trabajo"])

    def test_default_rules_come_from_config(self):
        df = movements([("2026-10-01", "NETFLIX.COM", 7990), ("2026-10-02", "METROGAS", 20000)])
        self.assertEqual(cat.categorize(df, cat.default_rules()).tolist(), ["Suscripciones", "Servicios"])


class SpendingTests(unittest.TestCase):
    def setUp(self):
        self.df = cat.with_categories(
            movements(
                [
                    ("2026-09-20", "LIDER", 10000),
                    ("2026-10-01", "LIDER", 20000),
                    ("2026-10-03", "LIDER", 5000),
                    ("2026-10-02", "UBER TRIP", 4500),
                    ("2026-10-04", "PAGO PESOS TEF", -30000),
                ]
            ),
            RULES,
        )

    def test_totals_per_category_in_a_month(self):
        totals = cat.spending(self.df, pd.Period("2026-10", "M"))
        self.assertEqual(totals[["Category", "Amount", "Count"]].values.tolist(), [["Supermercado", 25000, 2], ["Transporte", 4500, 1]])

    def test_daily_spending_fills_every_day(self):
        daily = cat.daily_spending(self.df, pd.Period("2026-10", "M"))
        self.assertEqual(len(daily), 31)
        self.assertEqual(daily["Amount"].iloc[0], 20000)
        self.assertEqual(daily["Amount"].sum(), 29500)

    def test_uncategorized_summary_groups_by_merchant(self):
        df = cat.with_categories(movements([("2026-10-01", "RARA 001", 1000), ("2026-10-02", "RARA 002", 2000)]), RULES)
        [row] = cat.uncategorized_summary(df).to_dict("records")
        self.assertEqual((row["Merchant"], row["Count"], row["Amount"]), ("rara", 2, 3000))


class BudgetTests(unittest.TestCase):
    def test_month_ratio(self):
        october = pd.Period("2026-10", "M")
        self.assertAlmostEqual(cat.month_ratio(october, datetime.date(2026, 10, 21)), 21 / 31)
        self.assertEqual(cat.month_ratio(october, datetime.date(2026, 11, 2)), 1.0)

    def test_budget_status(self):
        def line(spent, ratio=0.5):
            return cat.BudgetLine("Delivery", spent, 60000, ratio)

        self.assertEqual(line(20000).status, "ok")
        self.assertEqual(line(40000).status, "warning")  # ahead of the month's pace
        self.assertEqual(line(50000, ratio=0.9).status, "warning")  # >= 80%
        self.assertEqual(line(60000, ratio=0.99).status, "over")

    def test_budget_lines_only_for_categories_with_a_budget(self):
        spent = pd.DataFrame({"Category": ["Delivery"], "Amount": [48000]})
        cats = [cat.Category(1, "Delivery", 60000), cat.Category(2, "Hogar", None)]
        [line] = cat.budget_lines(cats, spent, pd.Period("2026-10", "M"), datetime.date(2026, 10, 21))
        self.assertEqual((line.category, line.spent, line.budget), ("Delivery", 48000, 60000))


class PersistenceTests(unittest.TestCase):
    def setUp(self):
        self.conn = history.connect(":memory:")

    def tearDown(self):
        self.conn.close()

    def category_id(self, name):
        return next(c.id for c in cat.list_categories(self.conn) if c.name == name)

    def test_history_starts_with_the_default_categories(self):
        names = {c.name for c in cat.list_categories(self.conn)}
        self.assertTrue({"Supermercado", "Delivery"} <= names)
        self.assertIn(cat.Rule("UBER EATS", "Delivery"), [cat.Rule(r.pattern, r.category) for r in cat.load_rules(self.conn)])

    def test_create_rename_budget_and_delete(self):
        new = cat.create_category(self.conn, "Mascotas", budget="30.000")
        cat.rename_category(self.conn, new, "Mascota")
        cat.set_budget(self.conn, new, "45000")
        [found] = [c for c in cat.list_categories(self.conn) if c.id == new]
        self.assertEqual((found.name, found.budget), ("Mascota", 45000))
        cat.delete_category(self.conn, new)
        self.assertNotIn(new, [c.id for c in cat.list_categories(self.conn)])

    def test_duplicate_and_reserved_names_are_rejected(self):
        with self.assertRaises(cat.CategoryError):
            cat.create_category(self.conn, "supermercado")
        with self.assertRaises(cat.CategoryError):
            cat.create_category(self.conn, cat.UNCATEGORIZED)

    def test_rule_learned_from_use_and_moved_between_categories(self):
        cat.add_rule(self.conn, "tienda rara", self.category_id("Hogar"))
        cat.add_rule(self.conn, "TIENDA RARA", self.category_id("Compras"))
        rules = [r for r in cat.load_rules(self.conn) if r.pattern == "TIENDA RARA"]
        self.assertEqual([r.category for r in rules], ["Compras"])

    def test_merge_moves_rules_and_movements(self):
        history.import_movements(self.conn, movements([("2026-10-01", "X", 1000)]))
        [movement_id] = history.load_movements(self.conn)["Id"]
        source, target = self.category_id("Combustible"), self.category_id("Transporte")
        cat.set_movement_category(self.conn, movement_id, source)
        cat.merge_categories(self.conn, source, target)

        self.assertEqual(cat.load_overrides(self.conn), {movement_id: "Transporte"})
        self.assertIn("COPEC", [r.pattern for r in cat.load_rules(self.conn) if r.category == "Transporte"])

    def test_deleting_a_category_sends_its_movements_back_to_the_rules(self):
        history.import_movements(self.conn, movements([("2026-10-01", "X", 1000)]))
        [movement_id] = history.load_movements(self.conn)["Id"]
        hogar = self.category_id("Hogar")
        cat.set_movement_category(self.conn, movement_id, hogar)
        cat.delete_category(self.conn, hogar)
        self.assertEqual(cat.load_overrides(self.conn), {})


if __name__ == "__main__":
    unittest.main()
