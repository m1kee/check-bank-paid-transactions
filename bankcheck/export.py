"""Pending purchases as text to paste (WhatsApp) or as CSV (proposal 19)."""
import csv
import datetime
import io

from bankcheck.formatting import CURRENCY_NAMES, format_amount

CSV_HEADER = ["Moneda", "Fecha", "Descripción", "Ciudad", "Monto"]


def pending_text(results: list, today: datetime.date = None) -> str:
    """
    Pendientes al 21/10/2026:
    • 03/10 UBER TRIP — $4.500
    Total: $4.500
    """
    today = today or datetime.date.today()
    with_unpaid = [r for r in results if not r.unpaid.empty]
    if not with_unpaid:
        return f"Sin pendientes al {today:%d/%m/%Y}."

    lines = [f"Pendientes al {today:%d/%m/%Y}:"]
    for result in with_unpaid:
        if len(with_unpaid) > 1 or result.currency != "CLP":
            lines.append(f"\n{CURRENCY_NAMES.get(result.currency, result.currency)}:")
        for row in result.unpaid.to_dict("records"):
            lines.append(f"• {row['Date']:%d/%m} {row['Description']} — {format_amount(row['Amount'], result.currency)}")
        lines.append(f"Total: {format_amount(result.total_unpaid, result.currency)}")
    return "\n".join(lines)


def pending_csv(results: list) -> str:
    """CSV with a BOM, so Excel opens the accents right."""
    out = io.StringIO()
    out.write("﻿")
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(CSV_HEADER)
    for result in results:
        for row in result.unpaid.to_dict("records"):
            writer.writerow([result.currency, f"{row['Date']:%Y-%m-%d}", row["Description"], row["City"], row["Amount"]])
    return out.getvalue()
