"""
Charts as HTML + CSS + inline SVG (proposal 14): no chart library, no external
files, so they work offline in the web app and in the HTML report, in light and
dark mode.

- Lines are SVG paths stretched to the plot (`preserveAspectRatio="none"` and
  non-scaling strokes); every text and dot is HTML on top, so nothing gets
  distorted on a phone.
- Marks carry their value in `data-tip` (+ `title` as a fallback). In the web
  app, static/charts.js turns them into tooltips, with a crosshair on lines.
  Tooltips only enhance: every chart sits next to a table with the same numbers.

Colors are roles (CSS variables inside .viz): slots 1-2 of the reference
categorical palette (this month = blue, previous month = orange, validated as a
pair in both modes), a gray for context marks (emphasis form) and the fixed
status colors for budgets, which always come with a text label.
"""
import json
import math
from html import escape

CSS = """
.viz {
    --viz-series: #2a78d6;
    --viz-previous: #eb6834;
    --viz-context: #b4b2a9;
    --viz-track: #e6eefa;
    --viz-grid: #ecebe6;
    --viz-axis: #c3c2b7;
    --viz-ink: #52514e;
    --viz-muted: #898781;
    --viz-surface: #fcfcfb;
    --viz-warning: #fab219;
    --viz-critical: #d03b3b;
    font-size: 0.75rem;
    color: var(--viz-ink);
    position: relative;
}
@media (prefers-color-scheme: dark) {
    :root:where(:not([data-theme="light"])) .viz {
        --viz-series: #3987e5;
        --viz-previous: #d95926;
        --viz-context: #55544f;
        --viz-track: #1f3350;
        --viz-grid: #2c2c2a;
        --viz-axis: #383835;
        --viz-ink: #c3c2b7;
        --viz-surface: #1a1a19;
    }
}
:root[data-theme="dark"] .viz {
    --viz-series: #3987e5;
    --viz-previous: #d95926;
    --viz-context: #55544f;
    --viz-track: #1f3350;
    --viz-grid: #2c2c2a;
    --viz-axis: #383835;
    --viz-ink: #c3c2b7;
    --viz-surface: #1a1a19;
}
.viz-empty { color: var(--viz-muted); padding: 24px 0; text-align: center; }
.viz-legend { display: flex; flex-wrap: wrap; gap: 6px 16px; margin: 0 0 12px; color: var(--viz-ink); }
.viz-legend span { display: inline-flex; align-items: center; gap: 6px; }
.viz-key { display: inline-block; width: 10px; height: 10px; border-radius: 3px; }
.viz-key.line { width: 14px; height: 2px; border-radius: 1px; }
.viz-key.series { background: var(--viz-series); }
.viz-key.previous { background: var(--viz-previous); }
.viz-key.context { background: var(--viz-context); }

/* Cartesian frame: y labels | plot, then x labels */
.viz-frame { display: grid; grid-template-columns: auto 1fr; column-gap: 8px; }
.viz-yaxis { position: relative; min-width: 28px; }
.viz-yaxis span { position: absolute; right: 0; transform: translateY(-50%); color: var(--viz-muted);
                  font-variant-numeric: tabular-nums; white-space: nowrap; }
.viz-plot { position: relative; border-bottom: 1px solid var(--viz-axis); }
.viz-grid { position: absolute; left: 0; right: 0; height: 1px; background: var(--viz-grid); }
.viz-xaxis { grid-column: 2; position: relative; height: 18px; margin-top: 6px; }
.viz-xaxis span { position: absolute; transform: translateX(-50%); color: var(--viz-muted); white-space: nowrap; }
.viz-xaxis span.first { transform: none; }
.viz-xaxis span.last { transform: translateX(-100%); }

/* Columns */
.viz-cols { position: absolute; inset: 0; display: flex; align-items: flex-end; gap: 2px; }
.viz-col { flex: 1; height: 100%; display: flex; align-items: flex-end; justify-content: center; min-width: 0; cursor: default; }
.viz-col > span { display: block; width: 100%; max-width: 24px; min-height: 1px; background: var(--viz-series); border-radius: 4px 4px 0 0; transition: filter .15s; }
.viz-col.context > span { background: var(--viz-context); }
.viz-col.is-hover > span, .viz-col:hover > span { filter: brightness(1.15); }

/* Lines */
.viz-plot svg { position: absolute; inset: 0; width: 100%; height: 100%; overflow: visible; }
.viz-plot path { fill: none; stroke-width: 2; stroke-linejoin: round; stroke-linecap: round; vector-effect: non-scaling-stroke; }
.viz-plot path.series { stroke: var(--viz-series); }
.viz-plot path.previous { stroke: var(--viz-previous); }
.viz-plot path.area { stroke: none; fill: var(--viz-series); opacity: .1; }
.viz-dot { position: absolute; width: 10px; height: 10px; border-radius: 50%; transform: translate(-50%, -50%);
           box-shadow: 0 0 0 2px var(--viz-surface); pointer-events: none; }
.viz-dot.series { background: var(--viz-series); }
.viz-dot.previous { background: var(--viz-previous); }
.viz-cross { position: absolute; top: 0; bottom: 0; width: 1px; background: var(--viz-axis); pointer-events: none; }
.viz-ref { position: absolute; left: 0; right: 0; border-top: 1px solid var(--viz-critical); pointer-events: none; }
.viz-ref span { position: absolute; right: 0; bottom: 2px; color: var(--viz-critical); background: var(--viz-surface); padding: 0 4px; border-radius: 4px; }
.viz-line .viz-plot { cursor: crosshair; touch-action: pan-y; }

/* Horizontal bars: label | bar | value */
.viz-bars { display: grid; grid-template-columns: minmax(84px, 32%) 1fr auto; gap: 10px 12px; align-items: center; }
.viz-bars .viz-label { overflow-wrap: anywhere; color: var(--viz-ink); font-size: 0.8125rem; }
.viz-bars .viz-value { text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; font-size: 0.8125rem; }
.viz-bars .viz-value small { color: var(--viz-muted); margin-left: 6px; }
.viz-track { display: flex; flex-direction: column; gap: 2px; }
.viz-bar { height: 12px; min-width: 2px; background: var(--viz-series); border-radius: 0 4px 4px 0; transition: filter .15s; }
.viz-bar.thin { height: 7px; }
.viz-bar.previous { background: var(--viz-previous); }
.viz-bar.is-hover, .viz-bar:hover { filter: brightness(1.15); }

/* Meters and sparklines */
.viz-meter { position: relative; height: 8px; border-radius: 4px; background: var(--viz-track); }
.viz-meter > span { position: absolute; inset: 0 auto 0 0; border-radius: 4px; background: var(--viz-series); }
.viz-meter.warning > span { background: var(--viz-warning); }
.viz-meter.over > span { background: var(--viz-critical); }
.viz-meter > i { position: absolute; top: -4px; bottom: -4px; width: 2px; border-radius: 1px; background: var(--viz-ink); }
.viz-spark { position: relative; height: 32px; }
.viz-spark svg { position: absolute; inset: 0; width: 100%; height: 100%; overflow: visible; }
.viz-spark path { fill: none; stroke: var(--viz-context); stroke-width: 2; vector-effect: non-scaling-stroke; stroke-linejoin: round; stroke-linecap: round; }
.viz-spark .viz-dot { width: 8px; height: 8px; }

/* Tooltip (one per page, built by charts.js) */
.viz-tooltip { position: fixed; z-index: 50; pointer-events: none; min-width: 120px; padding: 8px 10px; border-radius: 8px;
               background: #111; color: #f0efec; font-size: 0.8125rem; box-shadow: 0 8px 24px rgba(0,0,0,.25); }
.viz-tooltip-title { color: #c3c2b7; margin-bottom: 4px; }
.viz-tooltip-row { display: flex; align-items: center; gap: 8px; }
.viz-tooltip-row strong { font-variant-numeric: tabular-nums; }
.viz-tooltip-row .viz-key { width: 12px; height: 2px; }
.viz-tooltip-name { color: #c3c2b7; }
"""


def _pct(value: float, top: float) -> float:
    return max(0.0, min(100.0, 100.0 * value / top)) if top > 0 else 0.0


def nice_max(value: float) -> float:
    """The smallest 1 / 2 / 2.5 / 5 x 10^k at or above `value` (the top of a y axis)."""
    if value <= 0:
        return 1.0
    power = 10 ** math.floor(math.log10(value))
    return next(step * power for step in (1, 2, 2.5, 5, 10) if step * power >= value)


def _tip(title: str, value: str) -> str:
    return f'data-tip-title="{escape(title)}" data-tip="{escape(value)}" title="{escape(f"{title}: {value}")}"'


def _empty(text: str) -> str:
    return f'<div class="viz viz-empty">{escape(text)}</div>'


def _y_axis(top: float, format_axis, height: int) -> tuple:
    """(gutter HTML, gridlines HTML) for 0, top/2 and top."""
    labels, lines = [], []
    for fraction in (0, 0.5, 1):
        y = 100 - fraction * 100
        labels.append(f'<span style="top:{y:.1f}%">{escape(format_axis(top * fraction))}</span>')
        if fraction:
            lines.append(f'<div class="viz-grid" style="top:{y:.1f}%"></div>')
    return f'<div class="viz-yaxis" style="height:{height}px">{"".join(labels)}</div>', "".join(lines)


def _x_axis(labels: list, positions: list, pin_edges: bool = True) -> str:
    """Tick labels centered on their position; on lines the first and last are pinned inside the plot."""
    spans = []
    last = len(labels) - 1
    for i, (label, left) in enumerate(zip(labels, positions)):
        if label:
            edge = ""
            if pin_edges:
                edge = " first" if i == 0 else " last" if i == last and len(labels) > 1 else ""
            spans.append(f'<span class="{edge.strip()}" style="left:{left:.2f}%">{escape(label)}</span>')
    return f'<div class="viz-xaxis">{"".join(spans)}</div>'


def legend(items: list, line: bool = False) -> str:
    """`items`: (role, label) pairs; role is "series", "previous" or "context"."""
    shape = " line" if line else ""
    spans = "".join(f'<span><span class="viz-key{shape} {role}"></span>{escape(label)}</span>' for role, label in items)
    return f'<div class="viz-legend">{spans}</div>'


def columns(points: list, format_value, format_axis=None, tick_every: int = 1, emphasis: int = None,
            height: int = 180, empty: str = "Sin datos.") -> str:
    """
    Vertical columns. `points`: (tick label, value, tooltip title) tuples. Only every
    `tick_every`-th tick label is shown, so a month fits on a phone. With `emphasis`
    (an index), that column stays blue and the rest turn gray (context).
    """
    if not points or max(v for _, v, _ in points) <= 0:
        return _empty(empty)
    format_axis = format_axis or format_value
    top = nice_max(max(v for _, v, _ in points))
    gutter, grid = _y_axis(top, format_axis, height)
    cols = []
    for i, (_, value, title) in enumerate(points):
        context = " context" if emphasis is not None and i != emphasis else ""
        cols.append(f'<div class="viz-col{context}" {_tip(title, format_value(value))}>'
                    f'<span style="height:{_pct(value, top):.1f}%"></span></div>')
    n = len(points)
    positions = [100 * (i + 0.5) / n for i in range(n)]
    ticks = [tick if i % tick_every == 0 or i == n - 1 else "" for i, (tick, _, _) in enumerate(points)]
    # Only the last tick may sit right after the previous shown one; keep them apart
    if n > 1 and tick_every > 1 and (n - 1) % tick_every and (n - 1) % tick_every < tick_every / 2:
        ticks[n - 1 - (n - 1) % tick_every] = ""
    return (
        '<div class="viz" role="img" aria-label="Gráfico de columnas; los valores están en la tabla">'
        f'<div class="viz-frame">{gutter}<div class="viz-plot" style="height:{height}px">{grid}'
        f'<div class="viz-cols">{"".join(cols)}</div></div>'
        f'{_x_axis(ticks, positions, pin_edges=False)}</div></div>'
    )


def line(x_labels: list, series: list, format_value, format_axis=None, tick_every: int = 1,
         reference: tuple = None, height: int = 200, empty: str = "Sin datos.") -> str:
    """
    A line chart with a crosshair tooltip. `x_labels`: (tick label, tooltip title)
    per x position. `series`: dicts with "name", "role" ("series" / "previous"),
    "values" (None where there's no data yet) and optional "area". `reference`:
    (value, label) for a horizontal threshold, e.g. a budget.
    """
    all_values = [v for s in series for v in s["values"] if v is not None]
    if not all_values or len(x_labels) < 2:
        return _empty(empty)
    format_axis = format_axis or format_value
    top = nice_max(max(all_values + ([reference[0]] if reference else [])))
    gutter, grid = _y_axis(top, format_axis, height)
    n = len(x_labels)
    xs = [100 * i / (n - 1) for i in range(n)]

    paths, dots, data_series = [], [], []
    for s in series:
        ys = [None if v is None else 100 - _pct(v, top) for v in s["values"]]
        segments, current = [], []
        for x, y in zip(xs, ys):
            if y is None:
                if current:
                    segments.append(current)
                current = []
            else:
                current.append((x, y))
        if current:
            segments.append(current)
        for seg in segments:
            d = "M" + " L".join(f"{x:.3f} {y:.3f}" for x, y in seg)
            if s.get("area") and len(seg) > 1:
                paths.append(f'<path class="area" d="{d} L{seg[-1][0]:.3f} 100 L{seg[0][0]:.3f} 100 Z"/>')
            paths.append(f'<path class="{s["role"]}" d="{d}"/>')
        last = max((i for i, y in enumerate(ys) if y is not None), default=None)
        if last is not None and s["role"] == "series":
            dots.append(f'<span class="viz-dot series" style="left:{xs[last]:.2f}%;top:{ys[last]:.2f}%"></span>')
        data_series.append({
            "name": s["name"], "role": s["role"],
            "y": [None if y is None else round(y, 2) for y in ys],
            "v": [None if v is None else format_value(v) for v in s["values"]],
        })

    ref_html = ""
    if reference:
        ref_html = (f'<div class="viz-ref" style="top:{100 - _pct(reference[0], top):.2f}%">'
                    f'<span>{escape(reference[1])}</span></div>')
    hover_dots = "".join(f'<span class="viz-dot viz-hover-dot {s["role"]}" hidden></span>' for s in series)
    data = {"x": [title for _, title in x_labels], "series": data_series}
    ticks = [label if i % tick_every == 0 or i == n - 1 else "" for i, (label, _) in enumerate(x_labels)]
    if tick_every > 1 and (n - 1) % tick_every and (n - 1) % tick_every < tick_every / 2:
        ticks[n - 1 - (n - 1) % tick_every] = ""
    chart = (
        f'<div class="viz viz-line" data-chart="{escape(json.dumps(data))}" role="img" '
        'aria-label="Gráfico de líneas; los valores están en la tabla">'
        + (legend([(s["role"], s["name"]) for s in series], line=True) if len(series) > 1 else "")
        + f'<div class="viz-frame">{gutter}<div class="viz-plot" style="height:{height}px">{grid}{ref_html}'
        f'<svg viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">{"".join(paths)}</svg>'
        f'{"".join(dots)}<div class="viz-cross" hidden></div>{hover_dots}</div>'
        f'{_x_axis(ticks, xs)}</div></div>'
    )
    return chart


def bars(rows: list, format_value, previous_label: str = None, current_label: str = None,
         share: bool = False, empty: str = "Sin datos.") -> str:
    """
    Horizontal bars, in the order given. `rows`: (label, value) or (label, value,
    previous value) tuples; with previous values each row gets a second (orange)
    bar and a legend. `share` adds each row's percentage of the total.
    """
    if not rows:
        return _empty(empty)
    compare = previous_label is not None
    top = max(max(r[1], r[2] if compare else 0) for r in rows)
    total = sum(r[1] for r in rows if r[1] > 0)
    cells = []
    for row in rows:
        label, value = row[0], row[1]
        bar = (f'<div class="viz-bar{" thin" if compare else ""}" style="width:{_pct(value, top):.1f}%" '
               f'{_tip(f"{label} · {current_label}" if compare else label, format_value(value))}></div>')
        if compare:
            bar += (f'<div class="viz-bar thin previous" style="width:{_pct(row[2], top):.1f}%" '
                    f'{_tip(f"{label} · {previous_label}", format_value(row[2]))}></div>')
        pct = f"<small>{100 * value / total:.0f}%</small>" if share and total > 0 and value > 0 else ""
        cells.append(
            f'<div class="viz-label">{escape(label)}</div><div class="viz-track">{bar}</div>'
            f'<div class="viz-value">{escape(format_value(value))}{pct}</div>'
        )
    head = legend([("series", current_label), ("previous", previous_label)]) if compare else ""
    return f'<div class="viz">{head}<div class="viz-bars">{"".join(cells)}</div></div>'


def meter(ratio: float, marker: float = None, status: str = "ok", title: str = "") -> str:
    """A 0..1 progress bar; `marker` draws a line (e.g. how much of the month has passed)."""
    marker_html = f'<i style="left:calc({_pct(marker, 1):.1f}% - 1px)"></i>' if marker is not None else ""
    css_class = "" if status == "ok" else f" {status}"
    return (
        f'<div class="viz"><div class="viz-meter{css_class}" title="{escape(title)}">'
        f'<span style="width:{_pct(ratio, 1):.1f}%"></span>{marker_html}</div></div>'
    )


def sparkline(values: list, label: str = "") -> str:
    """A small trend line in the context gray, the last point in blue. "" with fewer than 2 values."""
    if len(values) < 2:
        return ""
    low, high = min(values), max(values)
    n = len(values)
    # A flat series sits in the middle instead of on the floor
    points = [(100 * i / (n - 1), 90 - 80 * (v - low) / (high - low) if high > low else 50) for i, v in enumerate(values)]
    d = "M" + " L".join(f"{x:.2f} {y:.2f}" for x, y in points)
    x, y = points[-1]
    return (
        f'<div class="viz viz-spark" role="img" aria-label="{escape(label or "Tendencia")}">'
        f'<svg viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true"><path d="{d}"/></svg>'
        f'<span class="viz-dot series" style="left:{x:.2f}%;top:{y:.2f}%"></span></div>'
    )
