import datetime
import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

import pandas as pd

from bankcheck import categories as cat
from bankcheck import history, notify
from bankcheck.analysis import analyze
from tests.helpers import movements

TODAY = datetime.date(2026, 10, 21)


class FakeNtfy:
    """A local HTTP server that records what would be published to ntfy."""

    def __init__(self, status=200):
        self.received = []
        received, code = self.received, status

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                body = self.rfile.read(int(self.headers["Content-Length"]))
                received.append({"path": self.path, "auth": self.headers.get("Authorization"), **json.loads(body)})
                self.send_response(code)
                self.end_headers()

            def log_message(self, *args):
                pass

        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_port}/mi-tema-secreto"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()


class SettingsTests(unittest.TestCase):
    def test_off_by_default(self):
        self.assertFalse(notify.NtfySettings().enabled)
        self.assertFalse(notify.send(notify.NtfySettings(), notify.sample_message()))

    def test_server_and_topic(self):
        settings = notify.NtfySettings(url="https://ntfy.sh/mi-tema")
        self.assertEqual(settings.server_and_topic, ("https://ntfy.sh", "mi-tema"))
        self.assertEqual(notify.NtfySettings(url="http://nas:8080/ntfy/tema/").server_and_topic, ("http://nas:8080/ntfy", "tema"))


class SendTests(unittest.TestCase):
    def setUp(self):
        self.ntfy = FakeNtfy()

    def tearDown(self):
        self.ntfy.close()

    def test_publishes_json_with_utf8_title_and_token(self):
        settings = notify.NtfySettings(url=self.ntfy.url, token="tk_123")
        self.assertTrue(notify.send(settings, notify.Message("⚠️ Presupuesto de Café", "Llevas el 85%", tags=("warning",))))
        [got] = self.ntfy.received
        self.assertEqual((got["path"], got["topic"], got["title"]), ("/", "mi-tema-secreto", "⚠️ Presupuesto de Café"))
        self.assertEqual(got["tags"], ["warning"])
        self.assertEqual(got["auth"], "Bearer tk_123")

    def test_failure_does_not_raise(self):
        with self.assertLogs("bankcheck.notify", "WARNING"):
            self.assertFalse(notify.send(notify.NtfySettings(url="http://127.0.0.1:9/tema"), notify.sample_message()))


class MessageTests(unittest.TestCase):
    def test_pending_summary(self):
        results = analyze(movements([("2026-10-09", "UBER TRIP", 4500), ("2026-10-15", "LIDER", 23450)]))
        message = notify.pending_summary(results, TODAY)
        self.assertEqual(message.body, "2 compras sin pagar · $27.950 · la más antigua tiene 12 días")
        self.assertNotIn("UBER", message.body)  # merchants only with details on

    def test_pending_summary_with_details(self):
        results = analyze(movements([("2026-10-09", "UBER TRIP", 4500)]))
        self.assertIn("UBER TRIP", notify.pending_summary(results, TODAY, details=True).body)

    def test_everything_paid(self):
        results = analyze(movements([("2026-10-09", "UBER", 4500), ("2026-10-10", "PAGO ONLINE", -4500)]))
        self.assertEqual(notify.pending_summary(results, TODAY).title, "✅ Todo pagado")

    def test_budget_levels(self):
        month = pd.Period("2026-10", "M")
        lines = [
            cat.BudgetLine("Delivery", 51000, 60000, 0.5),
            cat.BudgetLine("Supermercado", 130000, 120000, 0.5),
            cat.BudgetLine("Transporte", 1000, 15000, 0.5),
        ]
        warning, over = notify.budget_messages(lines, month)
        self.assertEqual(warning.key, "budget:Delivery:2026-10:80")
        self.assertIn("Llevas el 85% del presupuesto de octubre 2026", warning.body)
        self.assertEqual(over.key, "budget:Supermercado:2026-10:100")
        self.assertIn("Superaste", over.body)


class AfterImportTests(unittest.TestCase):
    def setUp(self):
        self.ntfy = FakeNtfy()
        self.settings = notify.NtfySettings(url=self.ntfy.url)
        self.conn = history.connect(":memory:")
        delivery = next(c.id for c in cat.list_categories(self.conn) if c.name == "Delivery")
        cat.set_budget(self.conn, delivery, 10000)
        history.import_movements(self.conn, movements([
            ("2026-10-05", "UBER EATS", 9000), ("2026-10-06", "CAFE", 2500), ("2026-10-06", "CAFE", 2500),
        ]))

    def tearDown(self):
        self.conn.close()
        self.ntfy.close()

    def titles(self):
        return [m["title"] for m in self.ntfy.received]

    def test_summary_budget_and_alert_then_only_the_summary(self):
        self.assertEqual(notify.notify_after_import(self.conn, self.settings, TODAY), 3)
        self.assertEqual(self.titles(), ["🧾 Compras sin pagar", "⚠️ Presupuesto de Delivery", "⚠️ Posible cobro duplicado"])

        self.ntfy.received.clear()
        notify.notify_after_import(self.conn, self.settings, TODAY)
        self.assertEqual(self.titles(), ["🧾 Compras sin pagar"])

    def test_passing_100_after_80_is_announced_again(self):
        notify.notify_after_import(self.conn, self.settings, TODAY)
        history.import_movements(self.conn, movements([("2026-10-12", "RAPPI", 5000)]))
        self.ntfy.received.clear()
        notify.notify_after_import(self.conn, self.settings, TODAY)
        self.assertIn("⛔ Presupuesto de Delivery", self.titles())

    def test_a_failed_message_is_retried_next_time(self):
        failing = FakeNtfy(status=500)
        try:
            with self.assertLogs("bankcheck.notify", "WARNING"):
                notify.notify_after_import(self.conn, notify.NtfySettings(url=failing.url), TODAY)
        finally:
            failing.close()
        notify.notify_after_import(self.conn, self.settings, TODAY)
        self.assertIn("⚠️ Presupuesto de Delivery", self.titles())

    def test_disabled_sends_nothing(self):
        self.assertEqual(notify.notify_after_import(self.conn, notify.NtfySettings(), TODAY), 0)
        self.assertEqual(self.ntfy.received, [])


if __name__ == "__main__":
    unittest.main()
