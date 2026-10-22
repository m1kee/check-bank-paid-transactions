import unittest

from bankcheck.analysis import analyze
from bankcheck.formatting import format_amount
from bankcheck.report_html import render_report
from tests.helpers import movements


class RenderReportTests(unittest.TestCase):
    def test_descriptions_are_escaped(self):
        html = render_report(analyze(movements([("2026-10-01", "<script>alert(1)</script> & co", 1000)])))
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt; &amp; co", html)

    def test_empty_state(self):
        html = render_report(analyze(movements([("2026-10-01", "PAGO ONLINE", -1000)])))
        self.assertIn("No hay compras de 1 cuota sin pagar", html)
        self.assertIn("Pagos sin compra asociada", html)

    def test_no_results(self):
        self.assertIn("No hay movimientos", render_report([]))

    def test_does_not_load_external_resources(self):
        html = render_report(analyze(movements([("2026-10-01", "UBER", 4500)])))
        self.assertNotIn("https://", html)


class FormatAmountTests(unittest.TestCase):
    def test_clp(self):
        self.assertEqual(format_amount(1234567), "$1.234.567")

    def test_usd(self):
        self.assertEqual(format_amount(1234.5, "USD"), "US$1.234,50")

    def test_invalid(self):
        self.assertEqual(format_amount("abc"), "$0")


if __name__ == "__main__":
    unittest.main()
