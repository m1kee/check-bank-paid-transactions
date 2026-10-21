"""Command-line entry point: read bank downloads, find unpaid purchases and open the HTML report."""
import argparse
import datetime
import os
import shutil
import sys
import webbrowser
from pathlib import Path

import pandas as pd

from bankcheck import __version__, config
from bankcheck.analysis import analyze
from bankcheck.dedup import merge_downloads
from bankcheck.formatting import CURRENCY_NAMES, format_amount
from bankcheck.parsers import ParseError, parse_file
from bankcheck.report_html import render_report


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
        nargs="+",
        help="Uno o más archivos de movimientos (.xls/.xlsx), en pesos o dólares. "
        "Ej: 'pre-process-data/movimientos.xls'",
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
            print(f"Archivo original archivado en: {archive_path}")
        except OSError as e:
            # The analysis can still run without archiving
            print(f"Aviso: no se pudo archivar '{path}': {e}", file=sys.stderr)


def print_report(results: list):
    print("\n--- REPORTE DE ANÁLISIS ---")
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
    print(f"\nReporte HTML generado en: {path}")
    try:
        webbrowser.open(Path(path).resolve().as_uri())
    except Exception as e:
        print(f"No se pudo abrir el navegador automáticamente: {e}")
    return path


def main():
    args = build_arg_parser().parse_args()

    print("=============================================")
    print(f"====== Account Analysis Tool v{__version__} ======")
    print("=============================================\n")
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")

    # 1. Read every file before touching anything on disk
    downloads = []
    for path in args.input_files:
        print(f"[Leyendo] {path}")
        try:
            parsed = parse_file(path)
        except ParseError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        for warning in parsed.warnings:
            print(f"Aviso: {warning}")
        print(f"  {len(parsed.movements)} movimientos ({', '.join(parsed.sections)})")
        downloads.append(parsed.movements)

    movements = merge_downloads(downloads)
    if len(downloads) > 1:
        print(f"Total sin duplicados: {len(movements)} movimientos")

    # 2. Save the clean file and archive the originals
    prefix = Path(args.output_prefix).stem if args.output_prefix else "cleaned-movements"
    clean_path = os.path.join(config.CLEAN_DATA_FOLDER, f"{prefix}_{timestamp}.xlsx")
    save_clean_file(movements, clean_path)
    print(f"\nArchivo limpio guardado en: {clean_path}")
    archive_inputs(args.input_files, timestamp)

    # 3. Analyze and report
    if args.start_date:
        print(f"\nFiltro de fecha activo: analizando desde {args.start_date:%Y-%m-%d}")
    results = analyze(movements, start_date=args.start_date)
    print_report(results)
    write_and_open_report(render_report(results, args.start_date), timestamp)

    print("\nProceso completo.")


if __name__ == "__main__":
    main()
