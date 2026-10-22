"""
Command-line entry point: read bank downloads, find unpaid purchases and open the HTML report.

Progress and problems go to stderr through `logging` (-v / -q change how much);
the analysis itself is printed to stdout, so it can be redirected to a file.
"""
import argparse
import datetime
import hashlib
import logging
import os
import shutil
import sys
import webbrowser
from pathlib import Path

import pandas as pd

from bankcheck import __version__, alerts, config, history, reconcile
from bankcheck import categories as cat
from bankcheck.alerts import KIND_LABELS
from bankcheck.analysis import analyze, filter_dates
from bankcheck.dedup import merge_downloads
from bankcheck.export import pending_csv
from bankcheck.formatting import CURRENCY_NAMES, format_amount
from bankcheck.insights import build_insights
from bankcheck.parsers import ParseError, parse_file, read_clean_file
from bankcheck.report_html import render_report

log = logging.getLogger("bankcheck")

LEVEL_PREFIXES = {logging.WARNING: "Aviso: ", logging.ERROR: "Error: ", logging.CRITICAL: "Error: "}


class CliError(Exception):
    """A problem with what the CLI was asked to do (shown as is)."""


class ConsoleFormatter(logging.Formatter):
    """Plain messages, with "Aviso:" / "Error:" in front of warnings and errors."""

    def format(self, record):
        return LEVEL_PREFIXES.get(record.levelno, "") + super().format(record)


def setup_logging(verbosity: int):
    """verbosity: -1 = only warnings and errors, 0 = progress, 1 = debug details."""
    level = {-1: logging.WARNING, 0: logging.INFO}.get(verbosity, logging.DEBUG)
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(ConsoleFormatter("%(message)s"))
    log.handlers[:] = [handler]
    log.setLevel(level)
    log.propagate = False


def parse_cli_date(value: str) -> datetime.datetime:
    try:
        return datetime.datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        raise argparse.ArgumentTypeError(f"fecha inválida '{value}', usa el formato YYYY-MM-DD")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Procesa y analiza archivos de movimientos del banco.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "input_files",
        nargs="*",
        help="Uno o más archivos de movimientos (.xls/.xlsx), en pesos o dólares. Sin archivos se procesan "
        f"todos los de '{config.INPUT_FOLDER}/'; si no hay ninguno y se usa --db, se revisa el historial.",
    )
    parser.add_argument(
        "-o", "--output",
        dest="output_prefix",
        help="Prefijo opcional para el archivo limpio. Ej: 'mi_reporte'",
    )
    parser.add_argument(
        "-d", "--start-date",
        dest="start_date",
        type=parse_cli_date,
        help="Fecha de inicio del análisis (YYYY-MM-DD). Se ignoran los movimientos anteriores.",
    )
    parser.add_argument(
        "-e", "--end-date",
        dest="end_date",
        type=parse_cli_date,
        help="Fecha de fin del análisis (YYYY-MM-DD, inclusive).",
    )
    parser.add_argument(
        "--db",
        nargs="?",
        const=config.DB_PATH,
        metavar="RUTA",
        help="Importa los archivos al historial SQLite y analiza todo el historial, no solo "
        f"estas descargas (por defecto '{config.DB_PATH}').",
    )
    parser.add_argument(
        "--reanalyze",
        metavar="ARCHIVO",
        help="Analiza un archivo limpio ya guardado (data/*.xlsx) en vez de descargas del banco.",
    )
    parser.add_argument("--no-open", action="store_true", help="Genera el reporte HTML pero no abre el navegador.")
    parser.add_argument("--no-archive", action="store_true", help="No mueve los archivos de entrada.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="No escribe nada en disco (ni archivo limpio, ni archivado, ni reporte, ni historial): "
        "solo muestra el análisis.",
    )
    parser.add_argument("--export", metavar="ARCHIVO.csv", help="Guarda las compras pendientes en un CSV.")
    verbosity = parser.add_mutually_exclusive_group()
    verbosity.add_argument(
        "-v", "--verbose", dest="verbosity", action="store_const", const=1, default=0,
        help="Muestra más detalle (para depurar).",
    )
    verbosity.add_argument(
        "-q", "--quiet", dest="verbosity", action="store_const", const=-1,
        help="Solo muestra el reporte, avisos y errores.",
    )
    return parser


def save_clean_file(movements: pd.DataFrame, path: str):
    """Save the normalized movements with real dates, shown as DD/MM/YYYY in Excel."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        movements.to_excel(writer, index=False)
        sheet = writer.sheets["Sheet1"]
        date_col = movements.columns.get_loc("Date") + 1
        for (cell,) in sheet.iter_rows(min_row=2, min_col=date_col, max_col=date_col):
            cell.number_format = "DD/MM/YYYY"


def file_sha256(path: str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class HistoryData:
    """What the analysis needs from the history: movements and the decisions stored in it."""

    def __init__(self, movements, resolutions=None, dismissed=frozenset(), rules=None, overrides=None,
                 categories=None, dismissed_alerts=frozenset()):
        self.movements = movements
        self.resolutions = resolutions or {}
        self.dismissed = dismissed
        self.rules = rules if rules is not None else cat.default_rules()
        self.overrides = overrides or {}
        self.categories = categories or []
        self.dismissed_alerts = dismissed_alerts


def import_to_history(db_path: str, downloads: list, dry_run: bool = False) -> HistoryData:
    """
    Import each (path, movements) download into the history and return all of it.
    With `dry_run` the imports go to an in-memory copy and the file is left untouched.
    """
    conn = history.connect_copy(db_path) if dry_run else history.connect(db_path)
    try:
        for path, frame in downloads:
            result = history.import_movements(
                conn, frame, source_name=Path(path).name, sha256=file_sha256(path)
            )
            log.info(
                "[Historial] %s: %d movimientos nuevos, %d ya existían",
                Path(path).name, result.new_count, result.existing_count,
            )
        data = HistoryData(
            history.load_movements(conn),
            resolutions=reconcile.load_resolutions(conn),
            dismissed=reconcile.load_dismissed(conn),
            rules=cat.load_rules(conn),
            overrides=cat.load_overrides(conn),
            categories=cat.list_categories(conn),
            dismissed_alerts=alerts.load_dismissed(conn),
        )
    finally:
        conn.close()
    log.info("[Historial] %d movimientos en total (%s)%s", len(data.movements), db_path,
             " · simulación: no se guardó nada" if dry_run else "")
    return data


def pending_inputs(folder: str) -> list:
    """The downloads waiting in `folder` (proposal 08), oldest first."""
    if not os.path.isdir(folder):
        return []
    paths = [p for p in Path(folder).iterdir() if p.suffix.lower() in (".xls", ".xlsx") and not p.name.startswith("~$")]
    return [str(p) for p in sorted(paths, key=lambda p: (p.stat().st_mtime, p.name))]


def archive_inputs(paths: list, timestamp: str):
    """Move the original files to the archive folder with a timestamped name."""
    os.makedirs(config.PROCESSED_ARCHIVE_FOLDER, exist_ok=True)
    for n, path in enumerate(paths, start=1):
        suffix = f"_{n}" if len(paths) > 1 else ""
        archive_path = os.path.join(
            config.PROCESSED_ARCHIVE_FOLDER, f"movements_{timestamp}{suffix}{Path(path).suffix}"
        )
        try:
            shutil.move(path, archive_path)
            log.info("Archivo original archivado en: %s", archive_path)
        except OSError as e:
            # The analysis can still run without archiving
            log.warning("no se pudo archivar '%s': %s", path, e)


def print_report(results: list, alerts: list = ()):
    print("--- REPORTE DE ANÁLISIS ---")
    if not results:
        print("No hay movimientos en el período analizado.")
    for result in results:
        fmt = lambda value: format_amount(value, result.currency)
        print(f"\n== {CURRENCY_NAMES.get(result.currency, result.currency)} ==")
        if result.unpaid.empty:
            print("¡Bien! Todas las compras de 1 cuota tienen un pago asociado.")
        else:
            print("COMPRAS SIN PAGO ASOCIADO:")
            for _, row in result.unpaid.iterrows():
                print(f"  {row['Date']:%d/%m/%Y}  {row['Description']:<40} {fmt(row['Amount']):>12}")
        if not result.orphan_payments.empty:
            print("PAGOS SIN COMPRA ASOCIADA:")
            for _, row in result.orphan_payments.iterrows():
                print(f"  {row['Date']:%d/%m/%Y}  {row['Description']:<40} {fmt(row['Amount']):>12}")
        for suggestion in result.suggestions:
            payment = suggestion.payment
            print(f"POSIBLE PAGO AGRUPADO: {payment['Date']:%d/%m/%Y} {payment['Description']} {fmt(payment['Amount'])}"
                  + (f" ({len(suggestion.options)} combinaciones posibles)" if suggestion.ambiguous else ""))
            for option in suggestion.options:
                print("  = " + " + ".join(f"{p['Description']} {fmt(p['Amount'])}" for p in option))
        if result.resolved is not None and not result.resolved.empty:
            print(f"Resueltas a mano: {len(result.resolved)}")
        print("---------------------------------")
        print(f"Total sin pagar:             {fmt(result.total_unpaid)}")
        print(f"Total pagos (1 cuota):       {fmt(result.total_payments)}")
        print(f"Total compras (1 cuota):     {fmt(result.total_purchases)}")
        print(f"Diferencia (pagos - compras): {fmt(result.difference)}")
    if alerts:
        print("\n== REVISAR ==")
        for alert in alerts:
            for row in alert.movements:
                print(f"  {KIND_LABELS[alert.kind]}: {row['Date']:%d/%m/%Y}  {row['Description']}  "
                      f"{format_amount(row['Amount'], row['Currency'])}")
    print("--- Análisis completo ---")


def write_and_open_report(html: str, timestamp: str, open_browser: bool = True) -> str:
    os.makedirs(config.REPORTS_FOLDER, exist_ok=True)
    path = os.path.join(config.REPORTS_FOLDER, f"report_{timestamp}.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    log.info("Reporte HTML generado en: %s", path)
    if not open_browser:
        return path
    try:
        webbrowser.open(Path(path).resolve().as_uri())
    except Exception as e:
        log.warning("no se pudo abrir el navegador automáticamente: %s", e)
    return path


def main(argv=None) -> int:
    """Run the CLI and return the exit code: 0 if everything went well, 1 on an error."""
    arg_parser = build_arg_parser()
    args = arg_parser.parse_args(argv)
    if args.reanalyze and (args.input_files or args.db):
        arg_parser.error("--reanalyze no se combina con archivos de entrada ni con --db")
    if args.dry_run and args.export:
        arg_parser.error("--dry-run no escribe nada en disco, así que no se combina con --export")
    if args.start_date and args.end_date and args.end_date < args.start_date:
        arg_parser.error("--end-date es anterior a --start-date")
    setup_logging(args.verbosity)

    try:
        run(args)
    except (CliError, ParseError, history.HistoryError) as e:
        log.error("%s", e)
        return 1
    return 0


def run(args):
    log.info("bankcheck v%s · análisis de movimientos", __version__)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")

    input_files = args.input_files
    if not input_files and not args.reanalyze:
        input_files = pending_inputs(config.INPUT_FOLDER)
        if input_files:
            log.info("Sin archivos indicados: se procesan los %d de '%s/'", len(input_files), config.INPUT_FOLDER)
        elif not args.db:
            raise CliError(
                f"No se indicaron archivos y no hay ninguno en '{config.INPUT_FOLDER}/'. "
                "Usa --db para revisar el historial."
            )

    # 1. Read every file before touching anything on disk
    downloads = []
    for path in input_files:
        log.info("[Leyendo] %s", path)
        parsed = parse_file(path)
        for warning in parsed.warnings:
            log.warning("%s", warning)
        log.info("  %d movimientos (%s)", len(parsed.movements), ", ".join(parsed.sections))
        downloads.append((path, parsed.movements))

    if args.reanalyze:
        log.info("[Reanalizando] %s", args.reanalyze)
        downloaded = read_clean_file(args.reanalyze)
    else:
        downloaded = merge_downloads([frame for _, frame in downloads])
    if len(downloads) > 1:
        log.info("Total sin duplicados: %d movimientos", len(downloaded))

    # 2. Add the downloads to the history, before the originals are moved
    data = import_to_history(args.db, downloads, args.dry_run) if args.db else HistoryData(downloaded)

    # 3. Save the clean file and archive the originals
    if downloads and not args.dry_run:
        prefix = Path(args.output_prefix).stem if args.output_prefix else "cleaned-movements"
        clean_path = os.path.join(config.CLEAN_DATA_FOLDER, f"{prefix}_{timestamp}.xlsx")
        save_clean_file(downloaded, clean_path)
        log.info("Archivo limpio guardado en: %s", clean_path)
        if not args.no_archive:
            archive_inputs(input_files, timestamp)

    # 4. Analyze and report
    if args.start_date or args.end_date:
        since = f"{args.start_date:%Y-%m-%d}" if args.start_date else "el inicio"
        until = f"{args.end_date:%Y-%m-%d}" if args.end_date else "hoy"
        log.info("Filtro de fecha activo: analizando desde %s hasta %s", since, until)
    results = analyze(data.movements, args.start_date, args.end_date, data.resolutions, data.dismissed)
    insights = build_insights(
        filter_dates(data.movements, args.start_date, args.end_date), data.rules, data.overrides, data.categories,
        dismissed_alerts=data.dismissed_alerts,
    )
    print_report(results, insights.alerts)

    if args.export:
        with open(args.export, "w", encoding="utf-8", newline="") as f:
            f.write(pending_csv(results))
        log.info("Pendientes exportados a: %s", args.export)
    if not args.dry_run:
        html = render_report(results, args.start_date, insights=insights, end_date=args.end_date)
        write_and_open_report(html, timestamp, open_browser=not args.no_open)


if __name__ == "__main__":
    sys.exit(main())
