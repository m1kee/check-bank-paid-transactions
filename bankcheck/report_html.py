"""Render the analysis as a self-contained dark-mode HTML page that works offline."""
import datetime
import json
from html import escape

import pandas as pd

from bankcheck import __version__, charts
from bankcheck.export import pending_csv, pending_text
from bankcheck.formatting import CURRENCY_NAMES, format_amount
from bankcheck.insights import month_name, pending_by_age
from bankcheck.reconcile import STATUS_LABELS

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

EXTRA_STYLE = """
details.table-container > summary { padding: 20px 24px; cursor: pointer; font-weight: 600; font-size: 1.1rem; }
details.table-container[open] > summary { border-bottom: 1px solid var(--border); }
.section-title { font-size: 1.25rem; margin: 40px 0 16px 0; font-weight: 600; }
.panel { background-color: var(--card-bg); border: 1px solid var(--border); border-radius: 12px; padding: 20px 24px; margin-bottom: 24px; }
.panel h3 { margin: 0 0 12px 0; font-size: 1rem; }
.actions { display: flex; gap: 12px; flex-wrap: wrap; justify-content: center; margin: 0 0 32px 0; }
.actions button { font: inherit; padding: 10px 16px; border-radius: 8px; border: 1px solid var(--border);
                  background: var(--card-bg); color: var(--text-main); cursor: pointer; }
.muted { color: var(--text-secondary); }
.tag { display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 0.8rem; border: 1px solid var(--border); }
.tag.warning { color: var(--warning); border-color: var(--warning); }
.tag.danger { color: var(--danger); border-color: var(--danger); }
"""

COPY_SCRIPT = """
<script>
(function () {
    var data = JSON.parse(document.getElementById("pending-data").textContent);
    function done(button, text) { var old = button.textContent; button.textContent = text; setTimeout(function () { button.textContent = old; }, 1500); }
    document.getElementById("copy-pending").addEventListener("click", function (event) {
        navigator.clipboard.writeText(data.text).then(function () { done(event.target, "¡Copiado!"); },
                                                      function () { window.prompt("Copia la lista:", data.text); });
    });
    document.getElementById("download-csv").addEventListener("click", function () {
        var link = document.createElement("a");
        link.href = URL.createObjectURL(new Blob([data.csv], { type: "text/csv;charset=utf-8" }));
        link.download = "pendientes.csv";
        link.click();
    });
})();
</script>"""


def _date(value) -> str:
    return value.strftime("%d/%m/%Y") if pd.notnull(value) else ""


def _card(title: str, value: str, tone: str) -> str:
    return f"""
        <div class="card">
            <h3>{escape(title)}</h3>
            <p class="value {tone}">{escape(value)}</p>
        </div>"""


def _grid(headers: list, rows: list, empty: str = "") -> str:
    """A table: `headers` are (label, is_number); `rows` are lists of already escaped cells."""
    right = ' style="text-align: right;"'
    head = "".join(f"<th{right if num else ''}>{escape(h)}</th>" for h, num in headers)
    if not rows:
        body = f'<tr><td colspan="{len(headers)}" class="empty-state">{escape(empty)}</td></tr>'
    else:
        body = "".join(
            "<tr>" + "".join(
                f'<td class="amount-cell">{cell}</td>' if num else f"<td>{cell}</td>"
                for cell, (_, num) in zip(row, headers)
            ) + "</tr>"
            for row in rows
        )
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def _table(title: str, note: str, table: str, collapsed: bool = False) -> str:
    note_html = f"<p>{escape(note)}</p>" if note else ""
    if collapsed:
        return f"""
        <details class="table-container"><summary>{escape(title)}</summary>{note_html and f'<div class="table-header">{note_html}</div>'}{table}</details>"""
    return f"""
        <div class="table-container">
            <div class="table-header"><h2>{escape(title)}</h2>{note_html}</div>
            {table}
        </div>"""


MOVEMENT_HEADERS = [("Fecha", False), ("Descripción", False), ("Ciudad", False), ("Monto", True)]


def _movement_rows(df: pd.DataFrame, currency: str, amount_class: str) -> list:
    return [
        [escape(_date(row["Date"])), escape(str(row["Description"])), escape(str(row["City"])),
         f'<span class="{amount_class}">{escape(format_amount(row["Amount"], currency))}</span>']
        for row in df.to_dict("records")
    ]


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

    tables = _table(
        "Detalle de Compras No Pagadas", "",
        _grid(MOVEMENT_HEADERS, _movement_rows(result.unpaid, currency, "unpaid-amount"),
              "No hay compras de 1 cuota sin pagar. ¡Todo está en orden!"),
    )
    if result.suggestions:
        rows = []
        for suggestion in result.suggestions:
            payment = suggestion.payment
            options = "<br>".join(
                " + ".join(f"{escape(str(p['Description']))} ({escape(fmt(p['Amount']))})" for p in option)
                for option in suggestion.options
            )
            tag = ' <span class="tag warning">varias opciones</span>' if suggestion.ambiguous else ""
            rows.append([escape(_date(payment["Date"])), escape(str(payment["Description"])) + tag, options,
                         escape(fmt(payment["Amount"]))])
        tables += _table(
            "Posibles pagos agrupados",
            "Pagos que equivalen a la suma de varias compras pendientes. Son solo sugerencias: confírmalas "
            "en la app web (página Pendientes) para que dejen de aparecer como pendientes.",
            _grid([("Fecha", False), ("Pago", False), ("Podría cubrir", False), ("Monto", True)], rows),
        )
    if not result.orphan_payments.empty:
        tables += _table(
            "Pagos sin compra asociada",
            "Pagos que no calzan con ninguna compra del mismo monto en los días previos. "
            "Pueden cubrir varias compras juntas o una compra fuera del período analizado.",
            _grid(MOVEMENT_HEADERS, _movement_rows(result.orphan_payments, currency, "orphan-amount")),
        )
    if not result.matches.empty:
        rows = [
            [escape(str(m["Description"])), escape(_date(m["Date"])), escape(fmt(m["Amount"])),
             escape(str(m["Payment Description"])), escape(_date(m["Payment Date"])), escape(str(m["Days To Pay"]))]
            for m in result.matches.to_dict("records")
        ]
        tables += _table(
            f"Compras pagadas y su pago ({len(rows)})", "",
            _grid([("Compra", False), ("Fecha compra", False), ("Monto", True), ("Pago", False),
                   ("Fecha pago", False), ("Días", True)], rows),
            collapsed=True,
        )
    if result.resolved is not None and not result.resolved.empty:
        rows = [
            [escape(_date(r["Date"])), escape(str(r["Description"])), escape(STATUS_LABELS[r["Status"]]),
             escape(r["Reason"] or r["Payment Description"]), escape(fmt(r["Amount"]))]
            for r in result.resolved.to_dict("records")
        ]
        tables += _table(
            f"Resueltas manualmente ({len(rows)})", "",
            _grid([("Fecha", False), ("Descripción", False), ("Estado", False), ("Motivo", False), ("Monto", True)], rows),
            collapsed=True,
        )

    return f"""
        {title}
        <div class="dashboard">{cards}
        </div>
        {tables}"""


def _insights_section(insights, results) -> str:
    fmt = lambda value: format_amount(value, insights.currency)
    month, previous = insights.month, insights.month - 1
    parts = [f'<h2 class="section-title">Gastos de {escape(month_name(month))}</h2>']

    delta = insights.total_spent - insights.previous_spent
    parts.append(
        '<div class="dashboard">'
        + _card("Gastado este mes", fmt(insights.total_spent), "neutral")
        + _card(f"Vs {month_name(previous)}", ("+" if delta > 0 else "") + fmt(delta), "danger" if delta > 0 else "success")
        + "".join(
            _card(f"Cuotas por mes ({c})", format_amount(monthly, c), "neutral")
            for c, (monthly, _) in insights.plans_summary.items()
        )
        + "</div>"
    )

    daily = [(str(d.day), float(a), _date(d)) for d, a in zip(insights.daily["Date"], insights.daily["Amount"])]
    parts.append(f'<div class="panel"><h3>Gasto por día</h3>{charts.columns(daily, fmt, tick_every=5)}</div>')

    rows = [(r["Category"], float(r["Amount"]), float(r["Previous"])) for r in insights.spending.to_dict("records")]
    parts.append(
        '<div class="panel"><h3>Gasto por categoría</h3>'
        + charts.bars(rows, fmt, previous_label=month_name(previous), current_label=month_name(month))
        + "</div>"
    )
    parts.append(_table(
        "Detalle por categoría", "",
        _grid([("Categoría", False), ("Compras", True), (month_name(month), True), (month_name(previous), True)],
              [[escape(r["Category"]), str(int(r["Count"])), escape(fmt(r["Amount"])), escape(fmt(r["Previous"]))]
               for r in insights.spending.to_dict("records")], "Sin gastos este mes."),
        collapsed=True,
    ))

    for result in results:
        if not result.unpaid.empty:
            ages = pending_by_age(result)
            parts.append(
                f'<div class="panel"><h3>Pendiente por antigüedad ({escape(result.currency)})</h3>'
                + charts.bars(ages, lambda v, c=result.currency: format_amount(v, c)) + "</div>"
            )

    if insights.alerts:
        rows = [
            [escape(alert.label), escape(_date(row["Date"])), escape(str(row["Description"])),
             escape(alert.detail), escape(format_amount(row["Amount"], row["Currency"]))]
            for alert in insights.alerts for row in alert.movements
        ]
        parts.append(_table(
            "⚠️ Revisar", "Cobros que conviene mirar dos veces.",
            _grid([("Alerta", False), ("Fecha", False), ("Descripción", False), ("Detalle", False), ("Monto", True)], rows),
        ))

    if not insights.plans.empty:
        rows = [
            [escape(str(p["Description"])), f"{p['Current']:02d}/{p['Total']:02d}",
             escape(format_amount(p["Amount"], p["Currency"])), str(p["Remaining"]),
             escape(format_amount(p["Remaining Debt"], p["Currency"])), escape(month_name(p["Ends"], short=True))]
            for p in insights.plans.to_dict("records")
        ]
        summary = " · ".join(
            f"Compromiso mensual {format_amount(m, c)} · Deuda total {format_amount(d, c)}"
            for c, (m, d) in insights.plans_summary.items()
        )
        parts.append(_table(
            "Cuotas vigentes", summary,
            _grid([("Compra", False), ("Cuota", False), ("Valor cuota", True), ("Restantes", True),
                   ("Deuda restante", True), ("Termina", False)], rows),
        ))
        if not insights.projection.empty:
            points = [(month_name(m, short=True), float(a), month_name(m))
                      for m, a in zip(insights.projection["Month"], insights.projection["Amount"])]
            parts.append(f'<div class="panel"><h3>Cuotas por mes, próximos 12 meses</h3>{charts.columns(points, fmt, tick_every=2)}</div>')

    if insights.subscriptions:
        rows = [
            [escape(s.description), escape(format_amount(s.amount, s.currency)),
             escape(format_amount(s.annual_cost, s.currency)), escape(_date(s.last_date)),
             (f'<span class="tag danger">subió {escape(format_amount(s.price_change, s.currency))}</span>'
              if s.price_increased else "")]
            for s in insights.subscriptions
        ]
        parts.append(_table(
            "Suscripciones detectadas", "Cobros que se repiten cada mes por un monto parecido.",
            _grid([("Comercio", False), ("Monto", True), ("Al año", True), ("Último cobro", False), ("", False)], rows),
        ))
    return "".join(parts)


def _json_for_script(value) -> str:
    """JSON that can't close the <script> tag it lives in."""
    return json.dumps(value).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def render_report(results: list, start_date=None, generated_at=None, insights=None, end_date=None) -> str:
    """Return the full HTML page for a list of CurrencyAnalysis results (and, optionally, their Insights)."""
    generated_at = generated_at or datetime.datetime.now()
    filter_text = ""
    if start_date is not None or end_date is not None:
        since = _date(pd.Timestamp(start_date)) if start_date is not None else "el inicio"
        until = _date(pd.Timestamp(end_date)) if end_date is not None else "hoy"
        filter_text = f"<p class='subtitle'>Filtrado desde {escape(since)} hasta {escape(until)}</p>"

    actions = script = ""
    if results:
        show_titles = len(results) > 1 or results[0].currency != "CLP"
        body = "".join(_currency_section(result, show_titles) for result in results)
        if any(not r.unpaid.empty for r in results):
            data = {"text": pending_text(results, generated_at.date()), "csv": pending_csv(results)}
            actions = (
                '<div class="actions"><button id="copy-pending" type="button">Copiar lista de pendientes</button>'
                '<button id="download-csv" type="button">Descargar CSV</button></div>'
            )
            script = f'<script type="application/json" id="pending-data">{_json_for_script(data)}</script>{COPY_SCRIPT}'
    else:
        body = '<p class="subtitle">No hay movimientos en el período analizado.</p>'
    if insights is not None and not insights.categorized.empty:
        body += _insights_section(insights, results)

    return f"""<!DOCTYPE html>
<html lang="es" data-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reporte de Análisis Bancario</title>
    <style>{STYLE}{EXTRA_STYLE}{charts.CSS}</style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Análisis de Movimientos</h1>
            {filter_text}
            <p class="subtitle">Reporte generado el {generated_at.strftime('%d/%m/%Y a las %H:%M')}</p>
        </header>
        {actions}
        {body}
        <div class="footer">
            <p>Reporte generado automáticamente por bankcheck v{__version__}</p>
        </div>
    </div>
    {script}
</body>
</html>"""
