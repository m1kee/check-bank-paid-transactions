import unittest

from bankcheck.dedup import merge_downloads
from tests.helpers import movements


class MergeDownloadsTests(unittest.TestCase):
    def test_overlapping_downloads_equal_the_latest_one(self):
        day_10 = movements([("2026-10-02", "UBER", 4500), ("2026-10-08", "LIDER", 23450)])
        day_20 = movements(
            [("2026-10-02", "UBER", 4500), ("2026-10-08", "LIDER", 23450), ("2026-10-15", "COPEC", 30000)]
        )

        merged = merge_downloads([day_10, day_20])
        self.assertEqual(merged["Description"].tolist(), ["UBER", "LIDER", "COPEC"])

    def test_identical_movements_in_one_download_are_kept(self):
        coffees = movements([("2026-10-02", "CAFE", 2500), ("2026-10-02", "CAFE", 2500)])
        self.assertEqual(len(merge_downloads([coffees])), 2)
        self.assertEqual(len(merge_downloads([coffees, coffees])), 2)

    def test_later_download_with_one_more_identical_movement_adds_only_that_one(self):
        first = movements([("2026-10-02", "CAFE", 2500)])
        second = movements([("2026-10-02", "CAFE", 2500), ("2026-10-02", "CAFE", 2500)])
        self.assertEqual(len(merge_downloads([first, second])), 2)

    def test_same_amount_in_other_currency_is_a_different_movement(self):
        clp = movements([("2026-10-02", "STORE", 10)])
        usd = movements([("2026-10-02", "STORE", 10)], currency="USD")
        self.assertEqual(len(merge_downloads([clp, usd])), 2)

    def test_result_is_sorted_by_date(self):
        df = movements([("2026-10-05", "B", 1), ("2026-10-01", "A", 1)])
        self.assertEqual(merge_downloads([df])["Description"].tolist(), ["A", "B"])


if __name__ == "__main__":
    unittest.main()
