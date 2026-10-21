"""Render the analysis as a self-contained dark-mode HTML page."""
import datetime
from html import escape

import pandas as pd

from bankcheck import __version__
from bankcheck.formatting import CURRENCY_NAMES, format_amount

STYLE = """
:root {
    --bg-color: #121212;
    --card-bg: #1e1e1e;
    --text-main: #f3f4f6;
    --text-secondary: #9ca3af;
    --danger: #ef4444;
    --success: #10b981;
    --warning: #f59e0b;
    --border: #374151;
}
body {
    font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
    background-color: var(--bg-color);
    color: var(--text-main);
    margin: 0;
    padding: 40px 20px;
    line-height: 1.6;
}
.container { max-width: 1000px; margin: 0 auto; }
header { margin-bottom: 40px; text-align: center; }
h1 { font-size: 2.5rem; margin: 0 0 10px 0; font-weight: 700; }
.currency-title { font-size: 1.5rem; margin: 48px 0 20px 0; font-weight: 600; }
.subtitle { color: var(--text-secondary); font-size: 1.1rem; margin: 0; }
.dashboard {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 20px;
    margin-bottom: 40px;
}
.card {
    background-color: var(--card-bg);
    border-radius: 12px;
    padding: 24px;
    border: 1px solid var(--border);
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
}
.card h3 {
    color: var(--text-secondary);
    font-size: 0.9rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin: 0 0 10px 0;
    font-weight: 600;
}
.card .value { font-size: 1.8rem; font-weight: 700; margin: 0; }
.value.danger { color: var(--danger); }
.value.success { color: var(--success); }
.value.neutral { color: var(--text-main); }
.table-container {
    background-color: var(--card-bg);
    border-radius: 12px;
    border: 1px solid var(--border);
    overflow-x: auto;
    margin-bottom: 24px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}
.table-header { padding: 20px 24px; border-bottom: 1px solid var(--border); }
.table-header h2 { margin: 0; font-size: 1.25rem; font-weight: 600; }
.table-header p { margin: 4px 0 0 0; color: var(--text-secondary); font-size: 0.9rem; }
table { width: 100%; border-collapse: collapse; text-align: left; }
th, td { padding: 16px 24px; border-bottom: 1px solid var(--border); }
th {
    background-color: rgba(255, 255, 255, 0.02);
    color: var(--text-secondary);
    font-weight: 600;
    font-size: 0.85rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
tr:last-child td { border-bottom: none; }
tr:hover td { background-color: rgba(255, 255, 255, 0.03); }
.amount-cell { text-align: right; font-family: monospace; font-size: 1.05rem; }
.unpaid-amount { color: var(--danger); font-weight: 600; }
.orphan-amount { color: var(--warning); font-weight: 600; }
.empty-state { text-align: center; padding: 40px !important; color: var(--success); font-weight: 500; }
.footer { text-align: center; margin-top: 40px; color: var(--text-secondary); font-size: 0.85rem; }
"""


def _date(value) -> str:
    return value.strftime("%d/%m/%Y") if pd.notnull(value) else ""


def _card(title: str, value: str, tone: str) -> str:
    return f"""
        <div class="card">
            <h3>{escape(title)}</h3>
            <p class="value {tone}">{escape(value)}</p>
        </div>"""


def _movement_rows(df: pd.DataFrame, currency: str, amount_class: str) -> str:
    rows = ""
    for _, row in df.iterrows():
        rows += f"""
            <tr>
                <td>{escape(_date(row["Date"]))}</td>
                <td>{escape(str(row["Description"]))}</td>
                <td>{escape(str(row["City"]))}</td>
                <td class="amount-cell {amount_class}">{escape(format_amount(row["Amount"], currency))}</td>
            </tr>"""
    return rows


def _table(title: str, note: str, rows: str) -> str:
    note_html = f"<p>{escape(note)}</p>" if note else ""
    return f"""
        <div class="table-container">
            <div class="table-header">
                <h2>{escape(title)}</h2>
                {note_html}
            </div>
            <table>
                <thead>
                    <tr>
                        <th>Fecha</th>
                        <th>Descripción</th>
                        <th>Ciudad</th>
                        <th style="text-align: right;">Monto</th>
                    </tr>
                </thead>
                <tbody>{rows}
                </tbody>
            </table>
        </div>"""


def _currency_section(result, show_title: bool) -> str:
    currency = result.currency
    fmt = lambda value: format_amount(value, currency)

    title = ""
    if show_title:
        title = f'<h2 class="currency-title">{escape(CURRENCY_NAMES.get(currency, currency))}</h2>'

    cards = (
        _card("Total por Pagar (Sin Empate)", fmt(result.total_unpaid), "danger")
        + _card("Total Pagos Registrados", fmt(result.total_payments), "success")
        + _card("Total Compras Registradas", fmt(result.total_purchases), "neutral")
        + _card(
            "Diferencia (Pagos - Compras)",
            fmt(result.difference),
            "success" if result.difference >= 0 else "danger",
        )
    )

    if result.unpaid.empty:
        unpaid_rows = """
            <tr>
                <td colspan="4" class="empty-state">No hay compras de 1 cuota sin pagar. ¡Todo está en orden!</td>
            </tr>"""
    else:
        unpaid_rows = _movement_rows(result.unpaid, currency, "unpaid-amount")

    tables = _table("Detalle de Compras No Pagadas", "", unpaid_rows)
    if not result.orphan_payments.empty:
        tables += _table(
            "Pagos sin compra asociada",
            "Pagos que no calzan con ninguna compra del mismo monto en los días previos. "
            "Pueden cubrir varias compras juntas o una compra fuera del período analizado.",
            _movement_rows(result.orphan_payments, currency, "orphan-amount"),
        )

    return f"""
        {title}
        <div class="dashboard">{cards}
        </div>
        {tables}"""


def render_report(results: list, start_date=None, generated_at=None) -> str:
    """Return the full HTML page for a list of CurrencyAnalysis results."""
    generated_at = generated_at or datetime.datetime.now()
    filter_text = ""
    if start_date is not None:
        filter_text = f"<p class='subtitle'>Filtrado desde: {escape(_date(pd.Timestamp(start_date)))}</p>"

    if results:
        show_titles = len(results) > 1 or results[0].currency != "CLP"
        body = "".join(_currency_section(result, show_titles) for result in results)
    else:
        body = '<p class="subtitle">No hay movimientos en el período analizado.</p>'

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reporte de Análisis Bancario</title>
    <style>{STYLE}</style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Análisis de Movimientos</h1>
            {filter_text}
            <p class="subtitle">Reporte generado el {generated_at.strftime('%d/%m/%Y a las %H:%M')}</p>
        </header>
        {body}
        <div class="footer">
            <p>Reporte generado automáticamente por Account Analysis Tool v{__version__}</p>
        </div>
    </div>
</body>
</html>"""
