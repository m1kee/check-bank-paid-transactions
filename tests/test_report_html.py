import unittest

from bankcheck.analysis import analyze
from bankcheck.categories import default_rules
from bankcheck.formatting import format_amount
from bankcheck.insights import build_insights
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


class FullReportTests(unittest.TestCase):
    def setUp(self):
        self.df = movements(
            [
                ("2026-09-14", "NETFLIX.COM", 7990),
                ("2026-08-14", "NETFLIX.COM", 7990),
                ("2026-10-14", "NETFLIX.COM", 7990),
                ("2026-10-01", "CAFE", 3000),
                ("2026-10-02", "UBER TRIP", 7000),
                ("2026-10-05", "PAGO ONLINE", -10000),
                ("2026-10-03", "FARMACIA", 2500),
                ("2026-10-04", "PAGO ONLINE", -2500),
                ("2026-10-06", "LIDER", 20000),
                ("2026-10-06", "LIDER", 20000),
                ("2026-10-07", "NOTEBOOK", 45000, "03/12"),
                ("2026-10-08", "</script><b>x</b>", 1000),
            ]
        )
        self.html = render_report(analyze(self.df), insights=build_insights(self.df, default_rules()))

    def test_every_section_is_there(self):
        for text in ("Posibles pagos agrupados", "Compras pagadas y su pago", "Gasto por categoría", "Gasto por día",
                     "Pendiente por antigüedad", "Revisar", "Cuotas vigentes", "Suscripciones detectadas",
                     "Copiar lista de pendientes"):
            self.assertIn(text, self.html)

    def test_still_works_offline(self):
        self.assertNotIn("https://", self.html)
        self.assertNotIn("<script src", self.html)

    def test_copy_data_cannot_break_out_of_its_script(self):
        self.assertNotIn("</script><b>", self.html)

    def test_alerts_section_hidden_without_alerts(self):
        df = movements([("2026-10-01", "UBER", 4500)])
        html = render_report(analyze(df), insights=build_insights(df, default_rules()))
        self.assertNotIn("Revisar", html)


class FormatAmountTests(unittest.TestCase):
    def test_clp(self):
        self.assertEqual(format_amount(1234567), "$1.234.567")

    def test_usd(self):
        self.assertEqual(format_amount(1234.5, "USD"), "US$1.234,50")

    def test_negative_sign_goes_first(self):
        self.assertEqual(format_amount(-38000), "-$38.000")
        self.assertEqual(format_amount(-9.99, "USD"), "-US$9,99")

    def test_invalid(self):
        self.assertEqual(format_amount("abc"), "$0")


if __name__ == "__main__":
    unittest.main()
