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

from bankcheck import __version__, config, history
from bankcheck.analysis import analyze
from bankcheck.dedup import merge_downloads
from bankcheck.formatting import CURRENCY_NAMES, format_amount
from bankcheck.parsers import ParseError, parse_file
from bankcheck.report_html import render_report

log = logging.getLogger("bankcheck")

LEVEL_PREFIXES = {logging.WARNING: "Aviso: ", logging.ERROR: "Error: ", logging.CRITICAL: "Error: "}


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
        help="Uno o más archivos de movimientos (.xls/.xlsx), en pesos o dólares. "
        "Ej: 'pre-process-data/movimientos.xls'. Con --db se puede omitir para revisar el historial.",
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
        "--db",
        nargs="?",
        const=config.DB_PATH,
        metavar="RUTA",
        help="Importa los archivos al historial SQLite y analiza todo el historial, no solo "
        f"estas descargas (por defecto '{config.DB_PATH}').",
    )
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


def import_to_history(db_path: str, downloads: list) -> pd.DataFrame:
    """Import each (path, movements) download into the history and return the whole history."""
    conn = history.connect(db_path)
    try:
        for path, frame in downloads:
            result = history.import_movements(
                conn, frame, source_name=Path(path).name, sha256=file_sha256(path)
            )
            log.info(
                "[Historial] %s: %d movimientos nuevos, %d ya existían",
                Path(path).name, result.new_count, result.existing_count,
            )
        movements = history.load_movements(conn)
    finally:
        conn.close()
    log.info("[Historial] %d movimientos en total (%s)", len(movements), db_path)
    return movements


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


def print_report(results: list):
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
        print("---------------------------------")
        print(f"Total sin pagar:             {fmt(result.total_unpaid)}")
        print(f"Total pagos (1 cuota):       {fmt(result.total_payments)}")
        print(f"Total compras (1 cuota):     {fmt(result.total_purchases)}")
        print(f"Diferencia (pagos - compras): {fmt(result.difference)}")
    print("--- Análisis completo ---")


def write_and_open_report(html: str, timestamp: str) -> str:
    os.makedirs(config.REPORTS_FOLDER, exist_ok=True)
    path = os.path.join(config.REPORTS_FOLDER, f"report_{timestamp}.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    log.info("Reporte HTML generado en: %s", path)
    try:
        webbrowser.open(Path(path).resolve().as_uri())
    except Exception as e:
        log.warning("no se pudo abrir el navegador automáticamente: %s", e)
    return path


def main(argv=None) -> int:
    """Run the CLI and return the exit code: 0 if everything went well, 1 on an error."""
    arg_parser = build_arg_parser()
    args = arg_parser.parse_args(argv)
    if not args.input_files and not args.db:
        arg_parser.error("indica al menos un archivo, o usa --db para analizar el historial")
    setup_logging(args.verbosity)

    try:
        run(args)
    except (ParseError, history.HistoryError) as e:
        log.error("%s", e)
        return 1
    return 0


def run(args):
    log.info("bankcheck v%s · análisis de movimientos", __version__)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")

    # 1. Read every file before touching anything on disk
    downloads = []
    for path in args.input_files:
        log.info("[Leyendo] %s", path)
        parsed = parse_file(path)
        for warning in parsed.warnings:
            log.warning("%s", warning)
        log.info("  %d movimientos (%s)", len(parsed.movements), ", ".join(parsed.sections))
        downloads.append((path, parsed.movements))

    downloaded = merge_downloads([frame for _, frame in downloads])
    if len(downloads) > 1:
        log.info("Total sin duplicados: %d movimientos", len(downloaded))

    # 2. Add the downloads to the history, before the originals are moved
    movements = import_to_history(args.db, downloads) if args.db else downloaded

    # 3. Save the clean file and archive the originals
    if downloads:
        prefix = Path(args.output_prefix).stem if args.output_prefix else "cleaned-movements"
        clean_path = os.path.join(config.CLEAN_DATA_FOLDER, f"{prefix}_{timestamp}.xlsx")
        save_clean_file(downloaded, clean_path)
        log.info("Archivo limpio guardado en: %s", clean_path)
        archive_inputs(args.input_files, timestamp)

    # 4. Analyze and report
    if args.start_date:
        log.info("Filtro de fecha activo: analizando desde %s", f"{args.start_date:%Y-%m-%d}")
    results = analyze(movements, start_date=args.start_date)
    print_report(results)
    write_and_open_report(render_report(results, args.start_date), timestamp)


if __name__ == "__main__":
    sys.exit(main())
