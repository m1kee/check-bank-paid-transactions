import unittest

from bankcheck.matching import is_payment_description, match_payments, split_movements
from tests.helpers import movements

PAY = "PAGO PESOS TEF PAGO NORMAL"


def run(rows, currency="CLP", **kwargs):
    purchases, payments = split_movements(movements(rows, currency))
    return match_payments(purchases, payments, **kwargs)


class PaymentDescriptionTests(unittest.TestCase):
    def test_mercadopago_comercialsana_is_not_treated_as_payment(self):
        self.assertFalse(is_payment_description("MERCADOPAGOCOMERCIALSANA"))

    def test_known_payment_terms_are_still_treated_as_payment(self):
        self.assertTrue(is_payment_description("PAGO PESOS TAR 1400"))
        self.assertTrue(is_payment_description("PAGO ONLINE"))

    def test_non_text_is_not_a_payment(self):
        self.assertFalse(is_payment_description(None))
        self.assertFalse(is_payment_description("   "))


class SplitMovementsTests(unittest.TestCase):
    def test_installment_purchases_are_left_out(self):
        purchases, payments = split_movements(
            movements([("2026-10-01", "NOTEBOOK", 45000, "03/12"), ("2026-10-01", "UBER", 4500)])
        )
        self.assertEqual(purchases["Description"].tolist(), ["UBER"])

    def test_payment_amounts_are_positive(self):
        _, payments = split_movements(movements([("2026-10-01", PAY, -4500)]))
        self.assertEqual(payments["Amount"].tolist(), [4500])


class MatchPaymentsTests(unittest.TestCase):
    def test_payment_after_purchase_pays_it(self):
        result = run([("2026-10-01", "UBER", 4500), ("2026-10-03", PAY, -4500)])
        self.assertTrue(result.unpaid.empty)
        self.assertTrue(result.orphan_payments.empty)
        self.assertEqual(result.matches["Days To Pay"].tolist(), [2])

    def test_payment_on_the_same_day_pays_it(self):
        result = run([("2026-10-01", "UBER", 4500), ("2026-10-01", PAY, -4500)])
        self.assertTrue(result.unpaid.empty)

    def test_payment_before_purchase_does_not_pay_it(self):
        result = run([("2026-10-06", PAY, -7490), ("2026-10-20", "APPLE.COM/BILL", 7490)])
        self.assertEqual(result.unpaid["Description"].tolist(), ["APPLE.COM/BILL"])
        self.assertEqual(len(result.orphan_payments), 1)

    def test_early_tolerance_allows_payment_slightly_before(self):
        rows = [("2026-10-01", PAY, -4500), ("2026-10-02", "UBER", 4500)]
        self.assertTrue(run(rows, early_tolerance_days=1).unpaid.empty)

    def test_repeated_amounts_pay_the_oldest_purchase_first(self):
        result = run(
            [
                ("2026-09-05", "NETFLIX SEP", 7990),
                ("2026-10-05", "NETFLIX OCT", 7990),
                ("2026-09-07", PAY, -7990),
            ]
        )
        self.assertEqual(result.unpaid["Description"].tolist(), ["NETFLIX OCT"])

    def test_old_algorithm_case_payment_between_two_equal_purchases(self):
        # One purchase before the payment and one after: only the earlier can be covered
        result = run(
            [
                ("2026-10-01", "CAFE A", 2500),
                ("2026-10-02", PAY, -2500),
                ("2026-10-05", "CAFE B", 2500),
            ]
        )
        self.assertEqual(result.unpaid["Description"].tolist(), ["CAFE B"])

    def test_payment_outside_the_window_does_not_pay(self):
        result = run([("2026-08-01", "LIDER", 23450), ("2026-10-01", PAY, -23450)], window_days=45)
        self.assertEqual(result.unpaid["Description"].tolist(), ["LIDER"])
        self.assertEqual(len(result.orphan_payments), 1)

    def test_different_amount_does_not_pay(self):
        result = run([("2026-10-01", "LIDER", 23450), ("2026-10-02", PAY, -23000)])
        self.assertEqual(len(result.unpaid), 1)
        self.assertEqual(len(result.orphan_payments), 1)

    def test_usd_decimals_match_exactly(self):
        result = run([("2026-10-01", "STEAM", 9.99), ("2026-10-02", "PAGO ONLINE", -9.99)], currency="USD")
        self.assertTrue(result.unpaid.empty)

    def test_match_shows_which_payment_covered_the_purchase(self):
        result = run([("2026-10-01", "UBER", 4500), ("2026-10-03", PAY, -4500)])
        row = result.matches.iloc[0]
        self.assertEqual(row["Description"], "UBER")
        self.assertEqual(row["Payment Description"], PAY)
        self.assertEqual(row["Payment Date"].strftime("%Y-%m-%d"), "2026-10-03")

    def test_no_movements(self):
        result = run([])
        self.assertTrue(result.unpaid.empty and result.matches.empty and result.orphan_payments.empty)


if __name__ == "__main__":
    unittest.main()
