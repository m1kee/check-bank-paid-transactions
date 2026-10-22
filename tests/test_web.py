import base64
import io
import os
import tempfile
import unittest

from fastapi.testclient import TestClient

from bankcheck import history
from bankcheck.analysis import analyze
from bankcheck.web.app import Settings, create_app
from tests.helpers import raw_export, raw_section

PAY = "PAGO PESOS TEF PAGO NORMAL"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def unpaid_part(page: str) -> str:
    """The pending list, without the "paid purchases" detail below it (04)."""
    return page.split("Compras pagadas y su pago")[0]


def xlsx(rows) -> bytes:
    """A synthetic bank download, as the bytes of an .xlsx file."""
    buffer = io.BytesIO()
    raw_export(raw_section(rows)).to_excel(buffer, header=False, index=False)
    return buffer.getvalue()


class WebTestCase(unittest.TestCase):
    password = None

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.settings = Settings(
            db_path=os.path.join(self.tmp.name, "bank.db"),
            uploads_dir=os.path.join(self.tmp.name, "uploads"),
            password=self.password,
        )
        self.client = TestClient(create_app(self.settings))

    def tearDown(self):
        self.client.close()
        self.tmp.cleanup()

    def upload(self, *files):
        return self.client.post(
            "/upload", files=[("files", (name, content, XLSX)) for name, content in files]
        )

    def load_history(self):
        conn = history.connect(self.settings.db_path)
        try:
            return history.load_movements(conn)
        finally:
            conn.close()


class UploadTests(WebTestCase):
    def test_upload_imports_and_reports_counts(self):
        response = self.upload(("sep.xlsx", xlsx([("02/09/2026", "UBER", 4500), ("28/09/2026", "LIDER", 23450)])))
        self.assertEqual(response.status_code, 200)
        self.assertIn("2 movimientos nuevos", response.text)
        self.assertIn("0 ya existían", response.text)
        self.assertEqual(len(self.load_history()), 2)

    def test_uploading_the_same_file_twice_does_not_duplicate(self):
        content = xlsx([("02/09/2026", "UBER", 4500), ("28/09/2026", "LIDER", 23450)])
        self.upload(("sep.xlsx", content))
        response = self.upload(("sep.xlsx", content))
        self.assertIn("0 movimientos nuevos", response.text)
        self.assertIn("2 ya existían", response.text)
        self.assertEqual(len(self.load_history()), 2)

    def test_several_files_at_once(self):
        response = self.upload(
            ("a.xlsx", xlsx([("02/09/2026", "UBER", 4500)])),
            ("b.xlsx", xlsx([("02/09/2026", "UBER", 4500), ("03/09/2026", "CAFE", 2500)])),
        )
        self.assertIn("1 movimiento nuevo,", response.text)
        self.assertIn("1 ya existía.", response.text)
        self.assertEqual(len(self.load_history()), 2)

    def test_original_files_are_kept(self):
        self.upload(("mis movs.xlsx", xlsx([("02/09/2026", "UBER", 4500)])))
        [saved] = os.listdir(self.settings.uploads_dir)
        self.assertTrue(saved.endswith("_mis_movs.xlsx"))

    def test_a_bad_file_imports_nothing(self):
        response = self.upload(
            ("ok.xlsx", xlsx([("02/09/2026", "UBER", 4500)])),
            ("bad.xlsx", b"not an excel file"),
        )
        self.assertIn("No se importó nada", response.text)
        self.assertTrue(self.load_history().empty)
        self.assertEqual(os.listdir(self.settings.uploads_dir), [])

    def test_upload_form(self):
        response = self.client.get("/upload")
        self.assertEqual(response.status_code, 200)
        self.assertIn('type="file"', response.text)


class PendingTests(WebTestCase):
    def test_home_redirects_to_the_dashboard(self):
        response = self.client.get("/", follow_redirects=False)
        self.assertEqual(response.headers["location"], "/dashboard")

    def test_empty_history_invites_to_upload(self):
        response = self.client.get("/pending")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Aún no hay movimientos", response.text)

    def test_shows_unpaid_purchases_across_periods(self):
        self.upload(("sep.xlsx", xlsx([("02/09/2026", "UBER", 4500), ("28/09/2026", "LIDER", 23450)])))
        self.upload(("oct.xlsx", xlsx([("03/10/2026", PAY, -23450)])))

        response = self.client.get("/pending")
        self.assertIn("UBER", unpaid_part(response.text))
        self.assertIn("$4.500", response.text)
        self.assertNotIn("LIDER", unpaid_part(response.text))
        self.assertIn("LIDER", response.text)  # with the payment that covered it

    def test_matches_the_cli_analysis(self):
        self.upload(
            ("sep.xlsx", xlsx([("02/09/2026", "UBER", 4500), ("05/09/2026", "COPEC", 30000), ("06/09/2026", PAY, -4500)]))
        )
        [result] = analyze(self.load_history())
        page = unpaid_part(self.client.get("/pending").text)
        for description in result.unpaid["Description"]:
            self.assertIn(description, page)
        self.assertNotIn("UBER", page)

    def test_start_date_filter(self):
        self.upload(("sep.xlsx", xlsx([("02/09/2026", "OLD", 1000), ("20/09/2026", "NEW", 2000)])))
        page = self.client.get("/pending", params={"start": "2026-09-10"}).text
        self.assertIn("NEW", page)
        self.assertNotIn("OLD", page)

    def test_empty_start_date_is_ignored(self):
        self.assertEqual(self.client.get("/pending", params={"start": ""}).status_code, 200)

    def test_descriptions_are_escaped(self):
        self.upload(("x.xlsx", xlsx([("02/09/2026", "<script>alert(1)</script>", 1000)])))
        page = self.client.get("/pending").text
        self.assertNotIn("<script>alert(1)</script>", page)
        self.assertIn("&lt;script&gt;", page)


class MovementsTests(WebTestCase):
    def setUp(self):
        super().setUp()
        self.upload(
            ("sep.xlsx", xlsx([("02/09/2026", "UBER TRIP", 4500), ("10/09/2026", "LIDER", 23450), ("20/09/2026", "UBER EATS", 9000)]))
        )

    def test_lists_every_movement(self):
        page = self.client.get("/movements").text
        self.assertIn("3 movimientos", page)
        self.assertIn("<nav>", page)

    def test_search_and_date_filters(self):
        page = self.client.get("/movements", params={"q": "uber", "date_from": "2026-09-05", "date_to": ""}).text
        self.assertIn("UBER EATS", page)
        self.assertNotIn("UBER TRIP", page)
        self.assertNotIn("LIDER", page)

    def test_htmx_filter_returns_only_the_table(self):
        page = self.client.get(
            "/movements", params={"q": "lider"}, headers={"HX-Request": "true", "HX-Target": "movements-table"}
        ).text
        self.assertIn("LIDER", page)
        self.assertNotIn("<nav>", page)


class PasswordTests(WebTestCase):
    password = "secreta"

    def test_pages_require_the_password(self):
        response = self.client.get("/pending")
        self.assertEqual(response.status_code, 401)
        self.assertIn("Basic", response.headers["www-authenticate"])

    def test_wrong_password_is_rejected(self):
        self.assertEqual(self.client.get("/pending", auth=("yo", "otra")).status_code, 401)

    def test_right_password_with_any_user(self):
        self.assertEqual(self.client.get("/pending", auth=("cualquiera", "secreta")).status_code, 200)

    def test_basic_auth_header(self):
        token = base64.b64encode(b"x:secreta").decode()
        self.assertEqual(self.client.get("/pending", headers={"Authorization": f"Basic {token}"}).status_code, 200)

    def test_static_files_are_public(self):
        # CSS and htmx hold no data; pages and uploads are what the password protects
        self.assertEqual(self.client.get("/static/style.css").status_code, 200)


if __name__ == "__main__":
    unittest.main()
