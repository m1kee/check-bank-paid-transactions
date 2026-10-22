import unittest

from bankcheck import history, reconcile
from bankcheck.analysis import analyze
from tests.helpers import movements

PAY = "PAGO PESOS TEF PAGO NORMAL"


class HistoryCase(unittest.TestCase):
    def setUp(self):
        self.conn = history.connect(":memory:")

    def tearDown(self):
        self.conn.close()

    def load(self, rows):
        history.import_movements(self.conn, movements(rows))
        df = history.load_movements(self.conn)
        return df, dict(zip(df["Description"], df["Id"]))

    def analyze(self):
        [result] = analyze(
            history.load_movements(self.conn),
            resolutions=reconcile.load_resolutions(self.conn),
            dismissed=reconcile.load_dismissed(self.conn),
        )
        return result


class ManualResolutionTests(HistoryCase):
    def test_ignored_purchase_is_not_pending(self):
        _, ids = self.load([("2026-10-01", "NETFLIX", 7990), ("2026-10-02", "UBER", 4500)])
        reconcile.set_resolution(self.conn, ids["NETFLIX"], reconcile.IGNORED, "Lo paga mi hermano")

        result = self.analyze()
        self.assertEqual(result.unpaid["Description"].tolist(), ["UBER"])
        self.assertEqual(result.resolved["Reason"].tolist(), ["Lo paga mi hermano"])
        self.assertEqual(result.total_purchases, 4500)

    def test_purchase_marked_paid_is_not_pending_but_counts(self):
        _, ids = self.load([("2026-10-02", "LIDER", 23450)])
        reconcile.set_resolution(self.conn, ids["LIDER"], reconcile.PAID, "Transferencia 03/10")

        result = self.analyze()
        self.assertTrue(result.unpaid.empty)
        self.assertEqual(result.resolved["Status"].tolist(), [reconcile.PAID])
        self.assertEqual(result.total_purchases, 23450)

    def test_ignored_payment_is_not_an_orphan(self):
        _, ids = self.load([("2026-10-02", PAY, -50000)])
        reconcile.set_resolution(self.conn, ids[PAY], reconcile.IGNORED, "Pago de otra tarjeta")

        result = self.analyze()
        self.assertTrue(result.orphan_payments.empty)
        self.assertEqual(len(result.ignored_payments), 1)
        self.assertEqual(result.total_payments, 0)

    def test_clear_resolution_brings_it_back(self):
        _, ids = self.load([("2026-10-02", "LIDER", 23450)])
        reconcile.set_resolution(self.conn, ids["LIDER"], reconcile.IGNORED)
        reconcile.clear_resolution(self.conn, ids["LIDER"])
        self.assertEqual(self.analyze().unpaid["Description"].tolist(), ["LIDER"])

    def test_unknown_status_is_rejected(self):
        with self.assertRaises(ValueError):
            reconcile.set_resolution(self.conn, 1, "maybe")


class GroupedPaymentTests(HistoryCase):
    def test_payment_equal_to_three_purchases_is_suggested(self):
        self.load(
            [
                ("2026-10-01", "CAFE", 3000),
                ("2026-10-02", "UBER", 4500),
                ("2026-10-03", "FARMACIA", 2500),
                ("2026-10-05", PAY, -10000),
            ]
        )
        result = self.analyze()
        [suggestion] = result.suggestions
        self.assertEqual(suggestion.payment["Amount"], 10000)
        self.assertFalse(suggestion.ambiguous)
        self.assertEqual([p["Description"] for p in suggestion.options[0]], ["CAFE", "UBER", "FARMACIA"])
        # Only a suggestion: nothing is applied yet
        self.assertEqual(len(result.unpaid), 3)
        self.assertEqual(len(result.orphan_payments), 1)

    def test_ambiguous_suggestions_are_not_applied(self):
        self.load(
            [
                ("2026-10-01", "A", 3000),
                ("2026-10-01", "B", 7000),
                ("2026-10-02", "C", 4000),
                ("2026-10-02", "D", 6000),
                ("2026-10-05", PAY, -10000),
            ]
        )
        result = self.analyze()
        [suggestion] = result.suggestions
        self.assertTrue(suggestion.ambiguous)
        self.assertEqual(len(result.unpaid), 4)

    def test_accepting_a_group_resolves_purchases_and_payment(self):
        _, ids = self.load(
            [("2026-10-01", "CAFE", 3000), ("2026-10-02", "UBER", 7000), ("2026-10-05", PAY, -10000)]
        )
        reconcile.accept_group(self.conn, ids[PAY], [ids["CAFE"], ids["UBER"]])

        result = self.analyze()
        self.assertTrue(result.unpaid.empty)
        self.assertTrue(result.orphan_payments.empty)
        self.assertEqual(result.suggestions, [])
        self.assertEqual(set(result.resolved["Payment Description"]), {PAY})

    def test_undoing_the_payment_undoes_the_whole_group(self):
        _, ids = self.load(
            [("2026-10-01", "CAFE", 3000), ("2026-10-02", "UBER", 7000), ("2026-10-05", PAY, -10000)]
        )
        reconcile.accept_group(self.conn, ids[PAY], [ids["CAFE"], ids["UBER"]])
        reconcile.clear_resolution(self.conn, ids[PAY])
        self.assertEqual(len(self.analyze().unpaid), 2)

    def test_dismissed_payment_gets_no_more_suggestions(self):
        _, ids = self.load(
            [("2026-10-01", "CAFE", 3000), ("2026-10-02", "UBER", 7000), ("2026-10-05", PAY, -10000)]
        )
        reconcile.dismiss_suggestions(self.conn, ids[PAY])
        self.assertEqual(self.analyze().suggestions, [])

    def test_purchases_after_the_payment_or_too_old_are_not_used(self):
        self.load(
            [
                ("2026-08-01", "OLD", 3000),
                ("2026-10-02", "UBER", 7000),
                ("2026-10-06", "LATER", 3000),
                ("2026-10-05", PAY, -10000),
            ]
        )
        self.assertEqual(self.analyze().suggestions, [])

    def test_works_without_history_ids(self):
        [result] = analyze(movements([("2026-10-01", "A", 3000), ("2026-10-02", "B", 7000), ("2026-10-05", PAY, -10000)]))
        self.assertEqual(len(result.suggestions), 1)


class MatchDetailTests(unittest.TestCase):
    def test_each_paid_purchase_shows_its_payment(self):
        [result] = analyze(movements([("2026-10-03", "UBER TRIP", 4500), ("2026-10-05", "PAGO ONLINE", -4500)]))
        [row] = result.matches.to_dict("records")
        self.assertEqual((row["Description"], row["Payment Description"], row["Days To Pay"]), ("UBER TRIP", "PAGO ONLINE", 2))

    def test_end_date_limits_the_range(self):
        [result] = analyze(movements([("2026-09-10", "SEP", 1000), ("2026-10-10", "OCT", 2000)]), end_date="2026-09-30")
        self.assertEqual(result.unpaid["Description"].tolist(), ["SEP"])


if __name__ == "__main__":
    unittest.main()
