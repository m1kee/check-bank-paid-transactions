import unittest

from bankcheck.analysis import analyze
from bankcheck.parsers import ParseError, parse_raw
from tests.helpers import HEADER, raw_export, raw_section, raw_usd_section

ROWS = [
    ("21/10/2026", "UBER TRIP", 4500.0, "01/01", "SANTIAGO"),
    ("20/10/2026", "PAGO PESOS TEF PAGO NORMAL", -4500.0),
    ("19/10/2026", "NOTEBOOK", 45000.0, "03/12"),
]


class ParseRawTests(unittest.TestCase):
    def test_reads_national_section(self):
        parsed = parse_raw(raw_export(raw_section(ROWS)))

        df = parsed.movements
        self.assertEqual(parsed.sections, ["Movimientos Nacionales"])
        self.assertEqual(parsed.warnings, [])
        self.assertEqual(len(df), 3)
        self.assertEqual(df["Currency"].unique().tolist(), ["CLP"])
        self.assertEqual(df["Amount"].tolist(), [4500, -4500, 45000])
        self.assertEqual(str(df["Amount"].dtype), "int64")
        self.assertEqual(df["Date"].iloc[0].strftime("%Y-%m-%d"), "2026-10-21")
        self.assertEqual(df["Installments"].tolist(), ["01/01", "01/01", "03/12"])

    def test_missing_city_is_empty_string(self):
        df = parse_raw(raw_export(raw_section(ROWS))).movements
        self.assertEqual(df["City"].tolist(), ["SANTIAGO", "", ""])

    def test_extra_metadata_rows_are_tolerated(self):
        df = parse_raw(raw_export(raw_section(ROWS), leading_rows=20)).movements
        self.assertEqual(len(df), 3)

    def test_reads_international_section_as_usd(self):
        section = raw_usd_section(
            [("05/10/2026", "STEAM PURCHASE COMPRAS INT.VI", 9.99), ("06/10/2026", "PAGO DOLAR TEF PAGOS INT.VIS", -9.99, "CHILE")]
        )
        parsed = parse_raw(raw_export(section))

        df = parsed.movements
        self.assertEqual(df["Currency"].tolist(), ["USD", "USD"])
        self.assertEqual(df["Amount"].tolist(), [9.99, -9.99])
        # No installment columns: every purchase is a single charge
        self.assertEqual(df["Installments"].tolist(), ["01/01", "01/01"])
        # The bank's "Ciudad" holds phone numbers, so the country is kept instead
        self.assertEqual(df["City"].tolist(), ["ESTADOS UNIDOS", "CHILE"])
        self.assertEqual(parsed.warnings, [])

    def test_dollar_payment_covers_dollar_purchase(self):
        df = parse_raw(raw_export(raw_usd_section(
            [("05/10/2026", "NETFLIX.COM COMPRAS INT.VI", 15.99), ("08/10/2026", "PAGO DOLAR TEF PAGOS INT.VIS", -15.99, "CHILE")]
        ))).movements
        [result] = analyze(df)
        self.assertTrue(result.unpaid.empty)
        self.assertTrue(result.orphan_payments.empty)

    def test_international_section_with_the_national_layout_is_rejected(self):
        section = raw_section([("05/10/2026", "STEAM", 9.99)], title="Movimientos Internacionales")
        with self.assertRaises(ParseError):
            parse_raw(raw_export(section))

    def test_reads_both_sections_in_one_file(self):
        national = raw_section(ROWS)
        international = raw_usd_section([("05/10/2026", "STEAM PURCHASE", 9.99)])
        df = parse_raw(raw_export(national, international)).movements
        self.assertEqual(df["Currency"].value_counts().to_dict(), {"CLP": 3, "USD": 1})

    def test_unknown_file_raises(self):
        with self.assertRaisesRegex(ParseError, "ninguna sección"):
            parse_raw(raw_export([["algo", "distinto"]]))

    def test_changed_header_raises(self):
        header = dict(HEADER)
        header[4] = "Comercio"
        with self.assertRaisesRegex(ParseError, "encabezado no coincide"):
            parse_raw(raw_export(raw_section(ROWS, header=header)))

    def test_non_numeric_amount_raises(self):
        rows = ROWS + [("18/10/2026", "LIDER", "$ 1.000")]
        with self.assertRaisesRegex(ParseError, "no son números"):
            parse_raw(raw_export(raw_section(rows)))

    def test_rows_after_a_gap_are_reported(self):
        section = raw_section(ROWS)
        gap = [None] * len(section[0])
        section = section + [gap] + raw_section([("01/10/2026", "PERDIDA", 100.0)])[2:]

        parsed = parse_raw(raw_export(section))
        self.assertEqual(len(parsed.movements), 3)
        self.assertEqual(len(parsed.warnings), 1)
        self.assertIn("se ignoraron 1 filas", parsed.warnings[0])


if __name__ == "__main__":
    unittest.main()
