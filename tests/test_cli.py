import contextlib
import io
import os
import sqlite3
import tempfile
import unittest
from unittest import mock

from bankcheck import cli
from tests.helpers import raw_export, raw_section

PAY = "PAGO PESOS TEF PAGO NORMAL"


class CliTestCase(unittest.TestCase):
    """Run the CLI inside a temporary folder, without opening the browser."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cwd = os.getcwd()
        os.chdir(self.tmp.name)
        patcher = mock.patch("bankcheck.cli.webbrowser.open")
        patcher.start()
        self.addCleanup(patcher.stop)

    def tearDown(self):
        os.chdir(self.cwd)
        self.tmp.cleanup()

    def write_download(self, name, rows):
        raw_export(raw_section(rows)).to_excel(name, header=False, index=False)
        return name

    def run_cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cli.main(list(args))
        return code, out.getvalue(), err.getvalue()


class ExitCodeTests(CliTestCase):
    def test_success_returns_zero(self):
        path = self.write_download("movs.xlsx", [("02/09/2026", "UBER", 4500)])
        code, out, _ = self.run_cli(path)
        self.assertEqual(code, 0)
        self.assertIn("UBER", out)

    def test_missing_file_returns_one(self):
        code, out, err = self.run_cli("no-existe.xls")
        self.assertEqual(code, 1)
        self.assertIn("Error: No existe el archivo", err)
        self.assertEqual(out, "")

    def test_unreadable_file_moves_nothing(self):
        good = self.write_download("good.xlsx", [("02/09/2026", "UBER", 4500)])
        with open("bad.xlsx", "wb") as f:
            f.write(b"not an excel file")
        code, _, _ = self.run_cli(good, "bad.xlsx")
        self.assertEqual(code, 1)
        self.assertTrue(os.path.exists(good))

    def test_no_files_without_db_is_a_usage_error(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
            cli.main([])
        self.assertEqual(raised.exception.code, 2)


class OutputTests(CliTestCase):
    def test_progress_goes_to_stderr_and_report_to_stdout(self):
        path = self.write_download("movs.xlsx", [("02/09/2026", "UBER", 4500)])
        _, out, err = self.run_cli(path)
        self.assertIn("[Leyendo]", err)
        self.assertNotIn("[Leyendo]", out)
        self.assertIn("REPORTE DE ANÁLISIS", out)

    def test_quiet_hides_progress_but_keeps_the_report(self):
        path = self.write_download("movs.xlsx", [("02/09/2026", "UBER", 4500)])
        _, out, err = self.run_cli(path, "-q")
        self.assertEqual(err, "")
        self.assertIn("UBER", out)

    def test_verbose_shows_debug_details(self):
        path = self.write_download("movs.xlsx", [("02/09/2026", "UBER", 4500)])
        _, _, err = self.run_cli(path, "-v")
        self.assertIn("encabezado en la fila", err)

    def test_quiet_and_verbose_are_exclusive(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            cli.main(["x.xls", "-q", "-v"])


class HistoryCliTests(CliTestCase):
    def test_db_keeps_purchases_across_runs(self):
        sep = self.write_download("sep.xlsx", [("28/09/2026", "LIDER", 23450), ("29/09/2026", "UBER", 4500)])
        self.assertEqual(self.run_cli(sep, "--db", "h.db")[0], 0)
        octo = self.write_download("oct.xlsx", [("03/10/2026", PAY, -23450)])
        code, out, err = self.run_cli(octo, "--db", "h.db")

        self.assertEqual(code, 0)
        self.assertIn("1 movimientos nuevos", err)
        self.assertIn("UBER", out)
        self.assertNotIn("LIDER", out)

    def test_db_without_files_analyzes_the_history(self):
        sep = self.write_download("sep.xlsx", [("28/09/2026", "LIDER", 23450)])
        self.run_cli(sep, "--db", "h.db")
        code, out, _ = self.run_cli("--db", "h.db")
        self.assertEqual(code, 0)
        self.assertIn("LIDER", out)

    def test_db_from_a_newer_version_returns_one(self):
        conn = sqlite3.connect("h.db")
        conn.execute("PRAGMA user_version = 999")
        conn.close()
        code, _, err = self.run_cli("--db", "h.db")
        self.assertEqual(code, 1)
        self.assertIn("Actualiza bankcheck", err)


if __name__ == "__main__":
    unittest.main()
