import datetime
import unittest

import pandas as pd

from bankcheck import billing, history
from bankcheck.analysis import analyze
from bankcheck.notify import pending_summary
from tests.helpers import movements

PAY = "PAGO DOLAR TEF PAGOS INT.VIS"
DAY_1 = datetime.datetime(2026, 10, 10, 9, 0)
DAY_2 = datetime.datetime(2026, 10, 21, 9, 0)


def usd(rows):
    return movements(rows, currency="USD")


class UpcomingStatementTests(unittest.TestCase):
    def setUp(self):
        self.conn = history.connect(":memory:")

    def tearDown(self):
        self.conn.close()

    def test_latest_download_is_what_the_next_statement_bills(self):
        history.import_movements(self.conn, usd([("2026-09-25", "NETFLIX.COM", 15.99), ("2026-10-02", "APPLE.COM", 2.99)]), now=DAY_1)
        # After the cut-off the view starts over: NETFLIX was billed, the payment shows up
        history.import_movements(
            self.conn, usd([("2026-10-02", "APPLE.COM", 2.99), ("2026-10-05", PAY, -40.00), ("2026-10-15", "STEAM", 10.00)]),
            now=DAY_2,
        )
        [upcoming] = billing.load_upcoming(self.conn)
        self.assertEqual((upcoming.currency, upcoming.amount, upcoming.count), ("USD", 12.99, 2))
        self.assertEqual(upcoming.since, pd.Timestamp("2026-10-02"))
        self.assertEqual(upcoming.seen_at, DAY_2)

    def test_refunds_subtract(self):
        history.import_movements(self.conn, usd([("2026-10-02", "STORE", 30.00), ("2026-10-03", "STORE REFUND", -10.00)]))
        [upcoming] = billing.load_upcoming(self.conn)
        self.assertEqual(upcoming.amount, 20.00)

    def test_only_currencies_paid_by_statement(self):
        history.import_movements(self.conn, movements([("2026-10-02", "LIDER", 23450)]))
        self.assertEqual(billing.load_upcoming(self.conn), [])

    def test_view_with_only_the_payment(self):
        history.import_movements(self.conn, usd([("2026-10-05", PAY, -40.00)]))
        [upcoming] = billing.load_upcoming(self.conn)
        self.assertEqual((upcoming.amount, upcoming.count, upcoming.since), (0, 0, None))

    def test_a_pesos_download_does_not_change_the_dollar_view(self):
        history.import_movements(self.conn, usd([("2026-10-02", "STEAM", 10.00)]), now=DAY_1)
        history.import_movements(self.conn, movements([("2026-10-03", "LIDER", 23450)]), now=DAY_2)
        [upcoming] = billing.load_upcoming(self.conn)
        self.assertEqual((upcoming.amount, upcoming.seen_at), (10.00, DAY_1))


class NotificationTests(unittest.TestCase):
    def test_dollars_show_the_next_statement_and_pesos_the_pending(self):
        df = pd.concat([movements([("2026-10-09", "UBER", 4500)]), usd([("2026-10-02", "STEAM", 10.00)])], ignore_index=True)
        upcoming = [billing.UpcomingStatement("USD", 10.00, 1, pd.Timestamp("2026-10-02"), DAY_2)]
        body = pending_summary(analyze(df), datetime.date(2026, 10, 21), upcoming=upcoming).body
        self.assertIn("Pesos (CLP): 1 compra sin pagar · $4.500", body)
        self.assertIn("Dólares (USD): próxima facturación US$10,00 (1 compra)", body)
        self.assertNotIn("Dólares (USD): 1 compra sin pagar", body)


if __name__ == "__main__":
    unittest.main()
