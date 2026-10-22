"""Web pages for proposals 03, 04, 11, 12, 13, 14, 15, 16, 19, 20 and 30."""
import io
import unittest

from fastapi.testclient import TestClient

from bankcheck import categories as cat
from bankcheck import history
from bankcheck.notify import NtfySettings
from bankcheck.web.app import create_app
from tests.helpers import raw_export, raw_usd_section
from tests.test_notify import FakeNtfy
from tests.test_web import PAY, WebTestCase, unpaid_part, xlsx


class FeatureTestCase(WebTestCase):
    def ids(self):
        df = self.load_history()
        return dict(zip(df["Description"], df["Id"]))

    def category_id(self, name):
        conn = history.connect(self.settings.db_path)
        try:
            return next(c.id for c in cat.list_categories(conn) if c.name == name)
        finally:
            conn.close()

    def post(self, url, data, **kwargs):
        return self.client.post(url, data=data, follow_redirects=False, **kwargs)


class ReconciliationPagesTests(FeatureTestCase):
    def setUp(self):
        super().setUp()
        self.upload(("oct.xlsx", xlsx([
            ("01/10/2026", "CAFE", 3000), ("02/10/2026", "UBER", 7000), ("05/10/2026", PAY, -10000),
            ("06/10/2026", "NETFLIX", 7990), ("07/10/2026", "FARMACIA", 2500), ("08/10/2026", "PAGO ONLINE", -2500),
        ])))

    def test_pending_shows_suggestion_and_match_detail(self):
        page = self.client.get("/pending").text
        self.assertIn("Posibles pagos agrupados", page)
        self.assertIn("Compras pagadas y su pago (1)", page)
        self.assertIn("FARMACIA", page)

    def test_mark_purchase_paid_with_a_reason(self):
        ids = self.ids()
        response = self.post(f"/movements/{ids['NETFLIX']}/resolve", {"status": "paid", "reason": "Transferencia", "next": "/pending"})
        self.assertEqual(response.status_code, 303)
        page = self.client.get("/pending").text
        self.assertNotIn("NETFLIX", unpaid_part(page))
        self.assertIn("Transferencia", page)

    def test_undo(self):
        ids = self.ids()
        self.post(f"/movements/{ids['NETFLIX']}/resolve", {"status": "ignored"})
        self.post(f"/movements/{ids['NETFLIX']}/unresolve", {})
        self.assertIn("NETFLIX", unpaid_part(self.client.get("/pending").text))

    def test_accept_grouped_payment(self):
        ids = self.ids()
        self.post(f"/payments/{ids[PAY]}/accept-group", {"purchase_ids": [ids["CAFE"], ids["UBER"]]})
        page = self.client.get("/pending").text
        self.assertNotIn("Posibles pagos agrupados", page)
        self.assertNotIn("UBER", unpaid_part(page).split("Pendientes")[-1])

    def test_dismiss_suggestion(self):
        ids = self.ids()
        self.post(f"/payments/{ids[PAY]}/dismiss", {})
        self.assertNotIn("Posibles pagos agrupados", self.client.get("/pending").text)

    def test_unknown_status_is_rejected(self):
        ids = self.ids()
        self.assertEqual(self.post(f"/movements/{ids['NETFLIX']}/resolve", {"status": "x"}).status_code, 400)

    def test_redirect_stays_inside_the_app(self):
        ids = self.ids()
        response = self.post(f"/movements/{ids['NETFLIX']}/resolve", {"status": "ignored", "next": "https://evil.example"})
        self.assertEqual(response.headers["location"], "/pending")

    def test_copy_text_and_csv(self):
        page = self.client.get("/pending").text
        self.assertIn("Pendientes al", page)
        self.assertIn("• 06/10 NETFLIX — $7.990", page)
        response = self.client.get("/pending.csv")
        self.assertIn("text/csv", response.headers["content-type"])
        self.assertIn("attachment", response.headers["content-disposition"])
        self.assertIn("CLP,2026-10-06,NETFLIX,,7990", response.text)


class CategoryPagesTests(FeatureTestCase):
    def setUp(self):
        super().setUp()
        self.upload(("oct.xlsx", xlsx([("01/10/2026", "UBER EATS PEDIDO", 9000), ("02/10/2026", "TIENDA RARA 01", 5000)])))

    def test_movements_show_categories_and_filter_by_them(self):
        page = self.client.get("/movements").text
        self.assertIn("Delivery", page)
        page = self.client.get("/movements", params={"category": cat.UNCATEGORIZED}).text
        self.assertIn("TIENDA RARA", page)
        self.assertNotIn("UBER EATS", page)

    def test_change_category_in_place_offers_a_rule(self):
        ids = self.ids()
        hogar = self.category_id("Hogar")
        response = self.client.post(f"/movements/{ids['TIENDA RARA 01']}/category", data={"category_id": hogar},
                                    headers={"HX-Request": "true"})
        self.assertIn("¿Siempre que diga", response.text)
        self.assertIn('value="TIENDA RARA"', response.text)
        self.assertNotIn('class="nav"', response.text)

        rule = self.client.post("/rules", data={"pattern": "TIENDA RARA", "category_id": hogar}, headers={"HX-Request": "true"})
        self.assertIn("Listo", rule.text)

    def test_change_category_without_javascript_redirects(self):
        ids = self.ids()
        response = self.post(f"/movements/{ids['TIENDA RARA 01']}/category", {"category_id": self.category_id("Hogar"), "next": "/movements?q=tienda"})
        self.assertEqual(response.headers["location"], "/movements?q=tienda")

    def test_categories_page_lists_uncategorized_merchants(self):
        page = self.client.get("/categories").text
        self.assertIn("Sin categoría", page)
        self.assertIn("TIENDA RARA 01", page)

    def test_create_category_with_budget_and_rule(self):
        self.post("/categories", {"name": "Mascotas", "budget": "30000"})
        mascotas = self.category_id("Mascotas")
        self.post("/rules", {"pattern": "tienda rara", "category_id": mascotas, "next": "/categories"})
        page = self.client.get("/movements", params={"category": "Mascotas"}).text
        self.assertIn("TIENDA RARA", page)

    def test_errors_are_shown(self):
        response = self.post("/categories", {"name": "Delivery"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("Ya existe la categoría", response.text)

    def test_merge_route_is_not_taken_as_an_id(self):
        source, target = self.category_id("Combustible"), self.category_id("Transporte")
        response = self.post("/categories/merge", {"source_id": source, "target_id": target})
        self.assertEqual(response.status_code, 303)
        self.assertNotIn("Combustible", self.client.get("/categories").text)


class DashboardTests(FeatureTestCase):
    def test_empty_history(self):
        self.assertIn("Aún no hay movimientos", self.client.get("/dashboard").text)

    def test_spending_charts_budgets_and_alerts(self):
        self.post("/categories/" + str(self.category_id("Supermercado")), {"name": "Supermercado", "budget": "30000"})
        self.upload(("oct.xlsx", xlsx([
            ("10/09/2026", "LIDER", 10000), ("10/10/2026", "LIDER", 25000), ("11/10/2026", "CAFE", 2500), ("11/10/2026", "CAFE", 2500),
        ])))
        page = self.client.get("/dashboard").text
        self.assertIn("Gastos de octubre 2026", page)
        self.assertIn("$30.000", page)  # spent in October
        self.assertIn("Presupuestos", page)
        self.assertIn("viz-meter", page)
        self.assertIn("viz-bars", page)
        self.assertIn("Posible cobro duplicado", page)

    def test_choose_another_month(self):
        self.upload(("x.xlsx", xlsx([("10/09/2026", "LIDER", 10000), ("10/10/2026", "LIDER", 25000)])))
        self.assertIn("Gastos de septiembre 2026", self.client.get("/dashboard", params={"month": "2026-09"}).text)


class InstallmentsAndSubscriptionsTests(FeatureTestCase):
    def test_installments_page(self):
        self.upload(("x.xlsx", xlsx([("05/10/2026", "NOTEBOOK", 45000, "03/12")])))
        page = self.client.get("/installments").text
        self.assertIn("NOTEBOOK", page)
        self.assertIn("$405.000", page)
        self.assertIn("03/12", page)

    def test_subscriptions_page_flags_price_increase(self):
        self.upload(("x.xlsx", xlsx([
            ("14/07/2026", "NETFLIX.COM", 7990), ("14/08/2026", "NETFLIX.COM", 7990),
            ("14/09/2026", "NETFLIX.COM", 7990), ("14/10/2026", "NETFLIX.COM", 9990),
        ])))
        page = self.client.get("/subscriptions").text
        self.assertIn("NETFLIX.COM", page)
        self.assertIn("Subió $2.000", page)

    def test_empty_pages(self):
        self.assertIn("No hay compras en cuotas", self.client.get("/installments").text)
        self.assertIn("No se detectaron", self.client.get("/subscriptions").text)


class NextStatementPagesTests(FeatureTestCase):
    def test_dollars_show_what_the_next_statement_bills(self):
        buffer = io.BytesIO()
        raw_export(raw_usd_section([("02/10/2026", "STEAM", 10.00), ("05/10/2026", "NETFLIX.COM", 15.99)])).to_excel(
            buffer, header=False, index=False
        )
        self.upload(("dolares.xlsx", buffer.getvalue()))
        pending = self.client.get("/pending").text
        self.assertIn("A pagar en la próxima facturación", pending)
        self.assertIn("US$25,99", pending)
        self.assertIn("2 compras desde el 02/10/2026", pending)
        self.assertIn("Próxima facturación (USD)", self.client.get("/dashboard").text)

    def test_pesos_only_has_no_next_statement(self):
        self.upload(("pesos.xlsx", xlsx([("01/10/2026", "UBER", 4500)])))
        self.assertNotIn("próxima facturación", self.client.get("/pending").text)


class NotificationPagesTests(FeatureTestCase):
    def setUp(self):
        self.ntfy = FakeNtfy()
        super().setUp()

    def tearDown(self):
        super().tearDown()
        self.ntfy.close()

    def enable(self):
        self.settings.ntfy = NtfySettings(url=self.ntfy.url)
        self.client.close()
        self.client = TestClient(create_app(self.settings))

    def test_off_explains_how_to_turn_them_on(self):
        page = self.client.get("/upload").text
        self.assertIn("BANKCHECK_NTFY_URL", page)
        self.assertIn("están apagadas", self.client.post("/notifications/test").text)
        self.assertEqual(self.ntfy.received, [])

    def test_upload_sends_the_summary(self):
        self.enable()
        response = self.upload(("oct.xlsx", xlsx([("01/10/2026", "UBER", 4500)])))
        self.assertIn("1 notificación enviada", response.text)
        self.assertEqual(self.ntfy.received[0]["title"], "🧾 Compras sin pagar")

    def test_test_button(self):
        self.enable()
        self.assertIn("Notificación de prueba enviada", self.client.post("/notifications/test").text)
        self.assertEqual(len(self.ntfy.received), 1)


if __name__ == "__main__":
    unittest.main()
