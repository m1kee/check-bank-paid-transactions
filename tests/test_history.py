import datetime
import os
import sqlite3
import tempfile
import unittest

import pandas as pd

from bankcheck import history
from bankcheck.analysis import analyze
from tests.helpers import movements

PAY = "PAGO PESOS TEF PAGO NORMAL"
DAY_1 = datetime.datetime(2026, 10, 10, 9, 0)
DAY_2 = datetime.datetime(2026, 10, 20, 9, 0)


class HistoryTestCase(unittest.TestCase):
    def setUp(self):
        self.conn = history.connect(":memory:")

    def tearDown(self):
        self.conn.close()


class ImportTests(HistoryTestCase):
    def test_importing_two_downloads_of_the_same_month_does_not_duplicate(self):
        day_10 = movements([("2026-10-02", "UBER", 4500), ("2026-10-08", "LIDER", 23450)])
        day_20 = movements(
            [("2026-10-02", "UBER", 4500), ("2026-10-08", "LIDER", 23450), ("2026-10-15", "COPEC", 30000)]
        )

        first = history.import_movements(self.conn, day_10, now=DAY_1)
        second = history.import_movements(self.conn, day_20, now=DAY_2)

        self.assertEqual((first.new_count, first.existing_count), (2, 0))
        self.assertEqual((second.new_count, second.existing_count), (1, 2))
        self.assertEqual(history.load_movements(self.conn)["Description"].tolist(), ["UBER", "LIDER", "COPEC"])

    def test_importing_the_same_download_twice_changes_nothing(self):
        df = movements([("2026-10-02", "CAFE", 2500), ("2026-10-02", "CAFE", 2500)])
        history.import_movements(self.conn, df)
        result = history.import_movements(self.conn, df)
        self.assertEqual((result.new_count, result.existing_count), (0, 2))
        self.assertEqual(len(history.load_movements(self.conn)), 2)

    def test_tracks_first_and_last_time_a_movement_was_seen(self):
        history.import_movements(self.conn, movements([("2026-10-02", "UBER", 4500)]), now=DAY_1)
        history.import_movements(self.conn, movements([("2026-10-02", "UBER", 4500)]), now=DAY_2)

        [row] = history.load_movements(self.conn).to_dict("records")
        self.assertEqual(row["First Seen"], pd.Timestamp(DAY_1))
        self.assertEqual(row["Last Seen"], pd.Timestamp(DAY_2))

    def test_records_each_import(self):
        history.import_movements(
            self.conn, movements([("2026-10-02", "UBER", 4500)]), source_name="movs.xls", sha256="abc"
        )
        row = self.conn.execute("SELECT source_name, sha256, new_count, existing_count FROM imports").fetchone()
        self.assertEqual(row, ("movs.xls", "abc", 1, 0))

    def test_round_trip_keeps_values_and_types(self):
        df = pd.concat(
            [movements([("2026-10-02", "UBER", 4500)]), movements([("2026-10-03", "NETFLIX", 15.99)], currency="USD")],
            ignore_index=True,
        )
        history.import_movements(self.conn, df)
        loaded = history.load_movements(self.conn)

        self.assertEqual(loaded["Currency"].tolist(), ["CLP", "USD"])
        self.assertEqual(loaded["Amount"].tolist(), [4500, 15.99])
        self.assertEqual(loaded["Date"].tolist(), [pd.Timestamp("2026-10-02"), pd.Timestamp("2026-10-03")])
        self.assertEqual(loaded["Installments"].tolist(), ["01/01", "01/01"])

    def test_recent_imports_newest_first(self):
        history.import_movements(self.conn, movements([("2026-10-02", "UBER", 4500)]), source_name="a.xls", now=DAY_1)
        history.import_movements(self.conn, movements([("2026-10-02", "UBER", 4500)]), source_name="b.xls", now=DAY_2)
        [latest, first] = history.recent_imports(self.conn)
        self.assertEqual((latest["source_name"], latest["new_count"], latest["existing_count"]), ("b.xls", 0, 1))
        self.assertEqual(first["imported_at"], DAY_1)

    def test_load_filters_by_currency(self):
        history.import_movements(self.conn, movements([("2026-10-02", "STORE", 10)]))
        history.import_movements(self.conn, movements([("2026-10-02", "STORE", 10)], currency="USD"))
        self.assertEqual(history.load_movements(self.conn, currency="USD")["Currency"].tolist(), ["USD"])

    def test_provisional_movement_replaced_by_its_posted_version(self):
        # The view first shows the charge as "COPEC" and, once posted, as "COPEC COMPRAS"
        history.import_movements(
            self.conn, movements([("2026-10-02", "UBER", 4500), ("2026-10-16", "COPEC", 13850)]), now=DAY_1
        )
        history.import_movements(
            self.conn,
            movements([("2026-10-02", "UBER", 4500), ("2026-10-16", "COPEC COMPRAS", 13850), ("2026-10-21", PAY, -13850)]),
            now=DAY_2,
        )

        self.assertEqual(history.load_movements(self.conn)["Description"].tolist(), ["UBER", "COPEC COMPRAS", PAY])
        [result] = analyze(history.load_movements(self.conn))
        self.assertEqual(result.matches["Description"].tolist(), ["COPEC COMPRAS"])
        self.assertEqual(result.unpaid["Description"].tolist(), ["UBER"])

    def test_only_movements_within_the_new_download_dates_are_replaced(self):
        history.import_movements(
            self.conn, movements([("2026-09-28", "LIDER", 23450), ("2026-10-20", "JUMBO", 9990)]), now=DAY_1
        )
        # Older and newer than everything in this download: not replaced
        history.import_movements(self.conn, movements([("2026-10-05", "UBER", 4500), ("2026-10-15", "RAPPI", 8000)]), now=DAY_2)
        self.assertEqual(history.load_movements(self.conn)["Description"].tolist(), ["LIDER", "UBER", "RAPPI", "JUMBO"])

    def test_a_download_of_another_currency_replaces_nothing(self):
        history.import_movements(self.conn, movements([("2026-10-05", "UBER", 4500)]), now=DAY_1)
        history.import_movements(self.conn, movements([("2026-10-01", "STEAM", 10)], currency="USD"), now=DAY_2)
        history.import_movements(self.conn, movements([("2026-10-09", "NETFLIX", 16)], currency="USD"), now=DAY_2)
        self.assertEqual(history.load_movements(self.conn)["Description"].tolist(), ["STEAM", "UBER", "NETFLIX"])

    def test_a_replaced_movement_seen_again_comes_back(self):
        history.import_movements(self.conn, movements([("2026-10-02", "UBER", 4500), ("2026-10-03", "COPEC", 100)]), now=DAY_1)
        history.import_movements(self.conn, movements([("2026-10-02", "UBER", 4500), ("2026-10-03", "LIDER", 200)]), now=DAY_2)
        history.import_movements(self.conn, movements([("2026-10-02", "UBER", 4500), ("2026-10-03", "COPEC", 100)]), now=DAY_2)
        self.assertEqual(sorted(history.load_movements(self.conn)["Description"]), ["COPEC", "UBER"])

    def test_empty_history(self):
        loaded = history.load_movements(self.conn)
        self.assertTrue(loaded.empty)
        self.assertEqual(analyze(loaded), [])


class AnalysisOverHistoryTests(HistoryTestCase):
    def test_unpaid_purchase_stays_pending_after_the_period_closes(self):
        history.import_movements(self.conn, movements([("2026-09-28", "LIDER", 23450)]), now=DAY_1)
        # Next period: the bank's view no longer shows the purchase
        history.import_movements(self.conn, movements([("2026-10-05", "UBER", 4500)]), now=DAY_2)

        [result] = analyze(history.load_movements(self.conn))
        self.assertEqual(result.unpaid["Description"].tolist(), ["LIDER", "UBER"])

    def test_payment_in_next_period_covers_purchase_of_previous_period(self):
        history.import_movements(self.conn, movements([("2026-09-28", "LIDER", 23450)]), now=DAY_1)
        history.import_movements(self.conn, movements([("2026-10-03", PAY, -23450)]), now=DAY_2)

        [result] = analyze(history.load_movements(self.conn))
        self.assertTrue(result.unpaid.empty)
        self.assertTrue(result.orphan_payments.empty)
        self.assertEqual(result.matches["Description"].tolist(), ["LIDER"])


class SchemaTests(unittest.TestCase):
    def test_new_database_gets_the_latest_schema(self):
        with history.connect(":memory:") as conn:
            self.assertEqual(history.schema_version(conn), len(history.MIGRATIONS))

    def test_reopening_keeps_the_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "sub", "bank.db")
            conn = history.connect(path)
            history.import_movements(conn, movements([("2026-10-02", "UBER", 4500)]))
            conn.close()

            conn = history.connect(path)
            self.assertEqual(len(history.load_movements(conn)), 1)
            conn.close()

    def test_upgrading_a_v1_history_keeps_its_movements(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "bank.db")
            conn = history.connect(path)
            history.import_movements(conn, movements([("2026-10-02", "UBER", 4500)]))
            conn.close()
            # Turn it into a v1 history with data, as it was before migration v2
            conn = sqlite3.connect(path)
            conn.executescript(
                "DROP TABLE dismissed_alerts; DROP TABLE notifications; DROP TABLE resolutions; DROP TABLE dismissed_suggestions; DROP TABLE category_rules; "
                "ALTER TABLE movements DROP COLUMN category_id; ALTER TABLE movements DROP COLUMN replaced_by_import_id; "
                "DROP TABLE categories; PRAGMA user_version = 1;"
            )
            conn.close()

            conn = history.connect(path)
            self.assertEqual(history.schema_version(conn), len(history.MIGRATIONS))
            self.assertEqual(history.load_movements(conn)["Description"].tolist(), ["UBER"])
            self.assertGreater(conn.execute("SELECT COUNT(*) FROM category_rules").fetchone()[0], 0)
            conn.close()

    def test_refuses_a_database_from_a_newer_version(self):
        conn = sqlite3.connect(":memory:")
        conn.execute(f"PRAGMA user_version = {len(history.MIGRATIONS) + 1}")
        with self.assertRaises(history.HistoryError):
            history.migrate(conn)
        conn.close()


if __name__ == "__main__":
    unittest.main()
