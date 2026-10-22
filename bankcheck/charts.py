"""
Charts as plain HTML + CSS (proposal 14): no JavaScript and no external files,
so they work offline in the HTML report and in the web app, in light and dark
mode. Each mark carries its value as a tooltip (title), and every chart sits
next to a table with the same numbers.

Colors are roles (CSS variables inside .viz), defined once in CSS below: slots 1-2
of the reference categorical palette (validated as a pair in both modes) and
the fixed status colors for budgets, which always come with a text label.
"""
from html import escape

CSS = """
.viz {
    --viz-series: #2a78d6;
    --viz-previous: #eb6834;
    --viz-track: #cde2fb;
    --viz-grid: #e1e0d9;
    --viz-axis: #c3c2b7;
    --viz-ink: #52514e;
    --viz-muted: #898781;
    --viz-warning: #fab219;
    --viz-critical: #d03b3b;
    font-size: 0.8rem;
    color: var(--viz-ink);
}
@media (prefers-color-scheme: dark) {
    :root:where(:not([data-theme="light"])) .viz {
        --viz-series: #3987e5;
        --viz-previous: #d95926;
        --viz-track: #184f95;
        --viz-grid: #2c2c2a;
        --viz-axis: #383835;
        --viz-ink: #c3c2b7;
    }
}
:root[data-theme="dark"] .viz {
    --viz-series: #3987e5;
    --viz-previous: #d95926;
    --viz-track: #184f95;
    --viz-grid: #2c2c2a;
    --viz-axis: #383835;
    --viz-ink: #c3c2b7;
}
.viz-legend { display: flex; gap: 16px; margin: 0 0 8px; color: var(--viz-ink); }
.viz-key { display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin-right: 6px; vertical-align: -1px; }

/* Columns (one per day / month), growing from a single baseline */
.viz-cols { display: flex; align-items: stretch; gap: 2px; height: 160px; border-bottom: 1px solid var(--viz-axis);
            background: linear-gradient(var(--viz-grid) 1px, transparent 1px) 0 0 / 100% 50%; }
.viz-col { flex: 1; display: flex; align-items: flex-end; justify-content: center; min-width: 0; }
.viz-col > span { display: block; width: 100%; max-width: 24px; background: var(--viz-series); border-radius: 4px 4px 0 0; }
.viz-col:hover > span { filter: brightness(1.15); }
.viz-ticks { display: flex; gap: 2px; color: var(--viz-muted); margin-top: 4px; }
.viz-ticks > span { flex: 1; text-align: center; min-width: 0; white-space: nowrap; overflow: visible; }
.viz-max { color: var(--viz-muted); margin-bottom: 2px; font-variant-numeric: tabular-nums; }

/* Horizontal bars: label | bar | value */
.viz-bars { display: grid; grid-template-columns: minmax(80px, 30%) 1fr auto; gap: 6px 10px; align-items: center; }
.viz-bars .viz-label { overflow-wrap: anywhere; color: var(--viz-ink); }
.viz-bars .viz-value { text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }
.viz-track { display: flex; flex-direction: column; gap: 2px; }
.viz-bar { height: 12px; min-width: 2px; background: var(--viz-series); border-radius: 0 4px 4px 0; }
.viz-bar.thin { height: 6px; }
.viz-bar.previous { background: var(--viz-previous); }

/* Budget meters */
.viz-meter { position: relative; height: 10px; border-radius: 5px; background: var(--viz-track); }
.viz-meter > span { position: absolute; inset: 0 auto 0 0; border-radius: 5px; background: var(--viz-series); }
.viz-meter.warning > span { background: var(--viz-warning); }
.viz-meter.over > span { background: var(--viz-critical); }
.viz-meter > i { position: absolute; top: -4px; bottom: -4px; width: 2px; background: var(--viz-ink); }
"""


def _pct(value: float, top: float) -> float:
    return max(0.0, min(100.0, 100.0 * value / top)) if top > 0 else 0.0


def columns(points: list, format_value, tick_every: int = 1, empty: str = "Sin datos.") -> str:
    """
    Vertical columns. `points`: (tick label, value, tooltip label) tuples; only
    every `tick_every`-th tick label is shown, so a whole month fits on a phone.
    """
    if not points or max(v for _, v, _ in points) <= 0:
        return f'<p class="viz">{escape(empty)}</p>'
    top = max(v for _, v, _ in points)
    cols, ticks = [], []
    for i, (tick, value, label) in enumerate(points):
        title = escape(f"{label}: {format_value(value)}")
        cols.append(f'<div class="viz-col" title="{title}"><span style="height:{_pct(value, top):.1f}%"></span></div>')
        ticks.append(f"<span>{escape(tick) if i % tick_every == 0 else ''}</span>")
    return (
        f'<div class="viz" role="img" aria-label="Gráfico de columnas; los valores están en la tabla">'
        f'<div class="viz-max">{escape(format_value(top))}</div>'
        f'<div class="viz-cols">{"".join(cols)}</div><div class="viz-ticks">{"".join(ticks)}</div></div>'
    )


def bars(rows: list, format_value, previous_label: str = None, current_label: str = None,
         empty: str = "Sin datos.") -> str:
    """
    Horizontal bars, largest first as given. `rows`: (label, value) or
    (label, value, previous value) tuples; with previous values each row gets a
    second, gray bar and a legend.
    """
    if not rows:
        return f'<p class="viz">{escape(empty)}</p>'
    compare = previous_label is not None
    top = max(max(r[1], r[2] if compare else 0) for r in rows)
    legend = ""
    if compare:
        legend = (
            '<div class="viz-legend">'
            f'<span><span class="viz-key" style="background:var(--viz-series)"></span>{escape(current_label)}</span>'
            f'<span><span class="viz-key" style="background:var(--viz-previous)"></span>{escape(previous_label)}</span>'
            "</div>"
        )
    cells = []
    for row in rows:
        label, value = row[0], row[1]
        bar = (f'<div class="viz-bar{" thin" if compare else ""}" style="width:{_pct(value, top):.1f}%" '
               f'title="{escape(f"{label}: {format_value(value)}")}"></div>')
        if compare:
            bar += (f'<div class="viz-bar thin previous" style="width:{_pct(row[2], top):.1f}%" '
                    f'title="{escape(f"{label}, {previous_label}: {format_value(row[2])}")}"></div>')
        cells.append(
            f'<div class="viz-label">{escape(label)}</div><div class="viz-track">{bar}</div>'
            f'<div class="viz-value">{escape(format_value(value))}</div>'
        )
    return f'<div class="viz">{legend}<div class="viz-bars">{"".join(cells)}</div></div>'


def meter(ratio: float, marker: float = None, status: str = "ok", title: str = "") -> str:
    """A 0..1 progress bar; `marker` draws a line (e.g. how much of the month has passed)."""
    marker_html = f'<i style="left:calc({_pct(marker, 1):.1f}% - 1px)"></i>' if marker is not None else ""
    css_class = "" if status == "ok" else f" {status}"
    return (
        f'<div class="viz"><div class="viz-meter{css_class}" title="{escape(title)}">'
        f'<span style="width:{_pct(ratio, 1):.1f}%"></span>{marker_html}</div></div>'
    )
