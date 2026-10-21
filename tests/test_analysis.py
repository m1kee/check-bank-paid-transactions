import unittest

import pandas as pd

from bankcheck.analysis import analyze
from tests.helpers import movements

PAY = "PAGO PESOS TEF PAGO NORMAL"


class AnalyzeTests(unittest.TestCase):
    def test_totals(self):
        [result] = analyze(
            movements(
                [
                    ("2026-10-01", "UBER", 4500),
                    ("2026-10-02", PAY, -4500),
                    ("2026-10-03", "LIDER", 23450),
                ]
            )
        )
        self.assertEqual(result.currency, "CLP")
        self.assertEqual(result.total_unpaid, 23450)
        self.assertEqual(result.total_payments, 4500)
        self.assertEqual(result.total_purchases, 27950)
        self.assertEqual(result.difference, -23450)

    def test_currencies_are_analyzed_separately(self):
        df = pd.concat(
            [
                movements([("2026-10-01", "STORE", 10)]),
                movements([("2026-10-02", "PAGO ONLINE", -10)], currency="USD"),
            ],
            ignore_index=True,
        )
        clp, usd = analyze(df)
        self.assertEqual((clp.currency, usd.currency), ("CLP", "USD"))
        self.assertEqual(len(clp.unpaid), 1)
        self.assertEqual(len(usd.orphan_payments), 1)

    def test_start_date_ignores_older_movements(self):
        df = movements([("2026-09-01", "OLD", 1000), ("2026-10-01", "NEW", 2000)])
        [result] = analyze(df, start_date="2026-09-15")
        self.assertEqual(result.unpaid["Description"].tolist(), ["NEW"])

    def test_empty_period_returns_no_results(self):
        df = movements([("2026-09-01", "OLD", 1000)])
        self.assertEqual(analyze(df, start_date="2026-10-01"), [])


if __name__ == "__main__":
    unittest.main()
