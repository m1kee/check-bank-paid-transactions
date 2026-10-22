"""
Web app: upload the bank's downloads, see unpaid purchases and where the money
goes, and fix what the automatic matching and categories got wrong.

Pages are rendered server-side with Jinja2. Every change is a plain form POST
followed by a redirect, so the app works without JavaScript; HTMX only makes
changing a movement's category happen in place.
"""
import datetime
import hashlib
import logging
import os
import re
import secrets
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import RedirectResponse, Response
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from markupsafe import Markup

from bankcheck import __version__, charts, config, history, reconcile
from bankcheck import alerts as alerts_module
from bankcheck import billing
from bankcheck import categories as cat
from bankcheck.analysis import analyze
from bankcheck.export import pending_csv, pending_text
from bankcheck.formatting import CURRENCY_NAMES, compact_amount, format_amount
from bankcheck.insights import build_insights, latest_month, month_name, pending_by_age
from bankcheck.installments import installment_plans, projection, summary
from bankcheck.notify import NtfySettings, notify_after_import, sample_message, send
from bankcheck.parsers import ParseError, parse_file
from bankcheck.recurring import detect_subscriptions
from bankcheck.text import suggest_pattern

HERE = Path(__file__).parent

log = logging.getLogger(__name__)

# Rows shown at once in the movements table
MOVEMENTS_PAGE_SIZE = 300


@dataclass
class Settings:
    db_path: str = config.DB_PATH
    uploads_dir: str = config.UPLOADS_FOLDER
    # When set, every page asks for it (HTTP Basic, any user name)
    password: str = None
    ntfy: NtfySettings = field(default_factory=NtfySettings)

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            db_path=os.environ.get("BANKCHECK_DB", config.DB_PATH),
            uploads_dir=os.environ.get("BANKCHECK_UPLOADS_DIR", config.UPLOADS_FOLDER),
            password=os.environ.get("BANKCHECK_PASSWORD") or None,
            ntfy=NtfySettings.from_env(),
        )


@dataclass
class FileImport:
    name: str
    sections: list
    new_count: int
    existing_count: int
    warnings: list = field(default_factory=list)


@dataclass
class HistoryView:
    """The history plus every decision stored in it, ready for the analyses."""

    movements: pd.DataFrame
    resolutions: dict
    dismissed: set
    rules: list
    overrides: dict
    categories: list
    dismissed_alerts: set = frozenset()

    @classmethod
    def load(cls, conn) -> "HistoryView":
        return cls(
            movements=history.load_movements(conn),
            resolutions=reconcile.load_resolutions(conn),
            dismissed=reconcile.load_dismissed(conn),
            rules=cat.load_rules(conn),
            overrides=cat.load_overrides(conn),
            categories=cat.list_categories(conn),
            dismissed_alerts=alerts_module.load_dismissed(conn),
        )

    def analyze(self, start=None, end=None) -> list:
        return analyze(self.movements, start, end, self.resolutions, self.dismissed)

    def categorized(self) -> pd.DataFrame:
        return cat.with_categories(self.movements, self.rules, self.overrides)


def _safe_filename(name: str) -> str:
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(name or "archivo").name).strip("._")
    return stem or "archivo"


def _parse_date(value: str):
    """A YYYY-MM-DD form field; empty or invalid means "no filter"."""
    try:
        return datetime.date.fromisoformat(value) if value else None
    except ValueError:
        return None


def _parse_month(value: str):
    try:
        return pd.Period(value, freq="M") if value else None
    except ValueError:
        return None


def _date(value) -> str:
    return value.strftime("%d/%m/%Y") if pd.notnull(value) else ""


def _safe_next(value: str, default: str) -> str:
    """Only redirect inside the app (no "//host" or "https://...")."""
    return value if value and value.startswith("/") and not value.startswith("//") else default


def _back(url: str) -> RedirectResponse:
    return RedirectResponse(url, status_code=status.HTTP_303_SEE_OTHER)


def create_app(settings: Settings = None) -> FastAPI:
    settings = settings or Settings.from_env()
    basic = HTTPBasic(auto_error=False, realm="bankcheck")

    def require_password(credentials: HTTPBasicCredentials = Depends(basic)):
        if settings.password is None:
            return
        given = credentials.password.encode() if credentials else b""
        if not secrets.compare_digest(given, settings.password.encode()):
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED,
                detail="Contraseña incorrecta",
                headers={"WWW-Authenticate": 'Basic realm="bankcheck"'},
            )

    def get_db():
        conn = history.connect(settings.db_path)
        try:
            yield conn
        finally:
            conn.close()

    app = FastAPI(title="bankcheck", version=__version__, dependencies=[Depends(require_password)],
                  docs_url=None, redoc_url=None, openapi_url=None)
    app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")

    templates = Jinja2Templates(directory=HERE / "templates")
    templates.env.filters["money"] = format_amount
    templates.env.filters["date"] = _date
    templates.env.filters["month_name"] = month_name
    templates.env.filters["suggest_pattern"] = suggest_pattern
    templates.env.globals.update(
        version=__version__, currency_names=CURRENCY_NAMES, chart_css=Markup(charts.CSS),
        status_labels=reconcile.STATUS_LABELS, uncategorized=cat.UNCATEGORIZED, payments_category=cat.PAYMENTS,
        # Charts used per row (progress bars, trends); the functions escape their own text
        meter=lambda *args, **kwargs: Markup(charts.meter(*args, **kwargs)),
        sparkline=lambda *args, **kwargs: Markup(charts.sparkline(*args, **kwargs)),
    )

    def render(request: Request, name: str, status_code: int = 200, **context):
        return templates.TemplateResponse(request, name, context, status_code=status_code)

    # --- Home: where the money goes ------------------------------------------------

    @app.get("/")
    def home():
        return _back("/dashboard")

    @app.get("/dashboard")
    def dashboard(request: Request, month: str = "", currency: str = "CLP", conn=Depends(get_db)):
        view = HistoryView.load(conn)
        months = sorted(view.movements["Date"].dt.to_period("M").unique(), reverse=True)
        currencies = sorted(view.movements["Currency"].unique()) or ["CLP"]
        currency = currency if currency in currencies else currencies[0]
        selected = _parse_month(month) or latest_month(view.movements)
        insights = build_insights(view.movements, view.rules, view.overrides, view.categories, selected, currency,
                                  dismissed_alerts=view.dismissed_alerts)
        results = {r.currency: r for r in view.analyze()}
        pending = results.get(currency)

        fmt = lambda value: format_amount(value, currency)
        axis = lambda value: compact_amount(value, currency)
        previous = selected - 1
        days = list(insights.daily["Date"])

        # Pace: cumulative spending this month vs the previous one, by day of the month
        pace_days = max(len(insights.pace), len(insights.previous_pace))
        pad = lambda values: values + [None] * (pace_days - len(values))
        budget_total = sum(line.budget for line in insights.budgets)
        pace = charts.line(
            [(str(d), f"Día {d}") for d in range(1, pace_days + 1)],
            [
                {"name": month_name(selected), "role": "series", "values": pad(insights.pace), "area": True},
                {"name": month_name(previous), "role": "previous", "values": pad(insights.previous_pace)},
            ],
            fmt, axis, tick_every=5, height=220, empty="Sin gastos este mes.",
            reference=(budget_total, f"Presupuesto {axis(budget_total)}") if budget_total else None,
        )
        monthly = list(zip(insights.monthly["Month"], insights.monthly["Amount"]))
        chart_html = {
            "pace": Markup(pace),
            "monthly": Markup(charts.columns(
                [(month_name(m, short=True)[:3], float(a), month_name(m)) for m, a in monthly],
                fmt, axis, tick_every=2, emphasis=len(monthly) - 1, height=170,
            )),
            "daily": Markup(charts.columns(
                [(str(d.day), float(a), _date(d)) for d, a in zip(days, insights.daily["Amount"])],
                fmt, axis, tick_every=5, height=170, empty="Sin gastos este mes.",
            )),
            "categories": Markup(charts.bars(
                [(r["Category"], float(r["Amount"]), float(r["Previous"])) for r in insights.spending.to_dict("records")],
                fmt, previous_label=month_name(previous), current_label=month_name(selected), share=True,
                empty="Sin gastos este mes.",
            )),
            "age": Markup(charts.bars(pending_by_age(pending), fmt))
            if pending is not None and not pending.unpaid.empty else None,
            "projection": Markup(charts.columns(
                [(month_name(m, short=True)[:3], float(a), month_name(m))
                 for m, a in zip(insights.projection["Month"], insights.projection["Amount"])],
                fmt, axis, tick_every=2, height=150,
            )) if insights.projection is not None and not insights.projection.empty else None,
            "trend": Markup(charts.sparkline([a for _, a in monthly][-6:], "Gasto de los últimos 6 meses")),
        }
        budgets = [
            (line, Markup(charts.meter(line.ratio, line.month_ratio, line.status,
                                       f"{line.category}: {fmt(line.spent)} de {fmt(line.budget)}")))
            for line in insights.budgets
        ]
        # Duplicates and unusual amounts first; "new" merchants and cities are informative and can be many
        novelty_kinds = (alerts_module.NEW_MERCHANT, alerts_module.NEW_CITY)
        subscriptions = [s for s in insights.subscriptions if s.currency == currency]
        oldest = int((pd.Timestamp(datetime.date.today()) - pending.unpaid["Date"].min()).days)             if pending is not None and not pending.unpaid.empty else None
        return render(
            request, "dashboard.html", active="dashboard", insights=insights, months=months, month=selected,
            previous=previous, upcoming=billing.load_upcoming(conn, view.movements),
            important_alerts=[a for a in insights.alerts if a.kind not in novelty_kinds],
            novelties=[a for a in insights.alerts if a.kind in novelty_kinds],
            currencies=currencies, currency=currency, pending=pending, oldest=oldest, charts=chart_html,
            budgets=budgets, subscriptions=subscriptions, monthly=monthly,
            has_history=not view.movements.empty,
            silenced=alerts_module.silenced_merchants(view.dismissed_alerts),
            back_url=str(request.url.path) + (f"?{request.url.query}" if request.url.query else ""),
        )

    # --- Pending purchases and manual reconciliation (03, 04, 11, 19) ----------------

    @app.get("/pending")
    def pending(request: Request, start: str = "", end: str = "", conn=Depends(get_db)):
        start, end = _parse_date(start), _parse_date(end)
        view = HistoryView.load(conn)
        results = view.analyze(start, end)
        today = pd.Timestamp(datetime.date.today())
        for result in results:
            result.unpaid = result.unpaid.assign(Age=(today - result.unpaid["Date"]).dt.days)
        query = "&".join(f"{k}={v}" for k, v in (("start", start), ("end", end)) if v)
        return render(
            request, "pending.html", active="pending", results=results, start=start, end=end,
            has_history=not view.movements.empty, copy_text=pending_text(results),
            upcoming={u.currency: u for u in billing.load_upcoming(conn, view.movements)},
            age_charts={
                r.currency: Markup(charts.bars(pending_by_age(r), lambda v, c=r.currency: format_amount(v, c)))
                for r in results if not r.unpaid.empty
            },
            csv_url="/pending.csv" + (f"?{query}" if query else ""),
            back_url="/pending" + (f"?{query}" if query else ""),
        )

    @app.get("/pending.csv")
    def pending_download(start: str = "", end: str = "", conn=Depends(get_db)):
        results = HistoryView.load(conn).analyze(_parse_date(start), _parse_date(end))
        return Response(
            pending_csv(results), media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="pendientes_{datetime.date.today():%Y-%m-%d}.csv"'},
        )

    @app.post("/movements/{movement_id}/resolve")
    def resolve(movement_id: int, status_: str = Form(..., alias="status"), reason: str = Form(""),
                next: str = Form(""), conn=Depends(get_db)):
        try:
            reconcile.set_resolution(conn, movement_id, status_, reason)
        except ValueError as e:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
        return _back(_safe_next(next, "/pending"))

    @app.post("/movements/{movement_id}/unresolve")
    def unresolve(movement_id: int, next: str = Form(""), conn=Depends(get_db)):
        reconcile.clear_resolution(conn, movement_id)
        return _back(_safe_next(next, "/pending"))

    @app.post("/payments/{payment_id}/accept-group")
    def accept_group(payment_id: int, purchase_ids: list[int] = Form(...), next: str = Form(""), conn=Depends(get_db)):
        reconcile.accept_group(conn, payment_id, purchase_ids)
        return _back(_safe_next(next, "/pending"))

    @app.post("/payments/{payment_id}/dismiss")
    def dismiss(payment_id: int, next: str = Form(""), conn=Depends(get_db)):
        reconcile.dismiss_suggestions(conn, payment_id)
        return _back(_safe_next(next, "/pending"))

    # --- Alerts dismissed by hand (16) ---------------------------------------------------

    @app.post("/alerts/dismiss")
    def dismiss_alert(key: str = Form(...), next: str = Form(""), conn=Depends(get_db)):
        alerts_module.dismiss(conn, key)
        return _back(_safe_next(next, "/dashboard"))

    @app.post("/alerts/restore")
    def restore_alert(key: str = Form(...), next: str = Form(""), conn=Depends(get_db)):
        alerts_module.restore(conn, key)
        return _back(_safe_next(next, "/dashboard"))

    # --- Upload -----------------------------------------------------------------------

    def upload_page(request: Request, imports=None, error=None, notified=None, notice=None):
        conn = history.connect(settings.db_path)
        try:
            recent = history.recent_imports(conn)
        finally:
            conn.close()
        return render(request, "upload.html", active="upload", imports=imports, error=error,
                      notifications=settings.ntfy.enabled, notified=notified, notice=notice, recent=recent)

    @app.get("/upload")
    def upload_form(request: Request):
        return upload_page(request)

    @app.post("/notifications/test")
    def notification_test(request: Request):
        if not settings.ntfy.enabled:
            return upload_page(request, error="Las notificaciones están apagadas: define BANKCHECK_NTFY_URL.")
        if send(settings.ntfy, sample_message()):
            return upload_page(request, notice="Notificación de prueba enviada. Revisa la app de ntfy.")
        return upload_page(request, error="No se pudo enviar la notificación. Revisa BANKCHECK_NTFY_URL y el log.")

    @app.post("/upload")
    def upload(request: Request, files: list[UploadFile] = File(...), conn=Depends(get_db)):
        files = [f for f in files if f.filename]
        if not files:
            return upload_page(request, error="Elige al menos un archivo.")

        # Save and read every file before importing any, like the CLI
        os.makedirs(settings.uploads_dir, exist_ok=True)
        stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
        saved = []
        try:
            for upload_file in files:
                content = upload_file.file.read()
                sha256 = hashlib.sha256(content).hexdigest()
                path = os.path.join(
                    settings.uploads_dir, f"{stamp}_{sha256[:8]}_{_safe_filename(upload_file.filename)}"
                )
                with open(path, "wb") as f:
                    f.write(content)
                saved.append((upload_file.filename, path, sha256))
            parsed = [parse_file(path) for _, path, _ in saved]
        except ParseError as e:
            log.warning("Subida rechazada: %s", e)
            for _, path, _ in saved:
                os.remove(path)
            return upload_page(request, error=f"No se importó nada. {e}")

        imports = []
        for (name, path, sha256), parsed_file in zip(saved, parsed):
            result = history.import_movements(conn, parsed_file.movements, source_name=name, sha256=sha256)
            log.info("Importado %s: %d nuevos, %d ya existían", path, result.new_count, result.existing_count)
            imports.append(FileImport(name, parsed_file.sections, result.new_count,
                                      result.existing_count, parsed_file.warnings))
        notified = notify_after_import(conn, settings.ntfy) if settings.ntfy.enabled else None
        return upload_page(request, imports=imports, notified=notified)

    # --- Movements and their categories (13) -------------------------------------------

    @app.get("/movements")
    def movements_page(
        request: Request,
        q: str = "",
        currency: str = "",
        category: str = "",
        date_from: str = "",
        date_to: str = "",
        conn=Depends(get_db),
    ):
        date_from, date_to = _parse_date(date_from), _parse_date(date_to)
        view = HistoryView.load(conn)
        df = view.categorized()
        currencies = sorted(df["Currency"].unique())
        if currency:
            df = df[df["Currency"] == currency]
        if category:
            df = df[df["Category"] == category]
        if q:
            df = df[df["Description"].str.contains(q, case=False, regex=False)]
        if date_from:
            df = df[df["Date"] >= pd.Timestamp(date_from)]
        if date_to:
            df = df[df["Date"] <= pd.Timestamp(date_to)]
        df = df.iloc[::-1]  # newest first

        context = dict(
            active="movements", rows=df.head(MOVEMENTS_PAGE_SIZE).to_dict("records"), total=len(df),
            page_size=MOVEMENTS_PAGE_SIZE, q=q, currency=currency, currencies=currencies, category=category,
            categories=view.categories, overrides=view.overrides, date_from=date_from, date_to=date_to,
            back_url=str(request.url.path) + (f"?{request.url.query}" if request.url.query else ""),
        )
        # The filter form (HTMX) only needs the table
        is_filter = request.headers.get("HX-Target") == "movements-table"
        name = "_movements_table.html" if is_filter else "movements.html"
        return render(request, name, **context)

    @app.post("/movements/{movement_id}/category")
    def set_category(request: Request, movement_id: int, category_id: str = Form(""), next: str = Form(""),
                     conn=Depends(get_db)):
        chosen = int(category_id) if category_id else None
        cat.set_movement_category(conn, movement_id, chosen)
        if not request.headers.get("HX-Request"):
            return _back(_safe_next(next, "/movements"))

        view = HistoryView.load(conn)
        [row] = view.categorized().query("Id == @movement_id").to_dict("records")
        return render(request, "_movement_row.html", row=row, categories=view.categories,
                      overrides=view.overrides, offer_rule=chosen is not None, back_url=_safe_next(next, "/movements"))

    @app.get("/categories")
    def categories_page(request: Request, conn=Depends(get_db)):
        return _categories(request, conn)

    def _categories(request: Request, conn, error: str = None):
        view = HistoryView.load(conn)
        categorized = view.categorized()
        month = latest_month(view.movements)
        spent = cat.spending(categorized, month)
        return render(
            request, "categories.html", status_code=400 if error else 200, active="categories", error=error,
            categories=view.categories, rules=view.rules, month=month,
            history=cat.category_history(categorized, month),
            month_ratio=cat.month_ratio(month),
            spent=dict(zip(spent["Category"], spent["Amount"])),
            uncategorized=cat.uncategorized_summary(categorized).to_dict("records"),
        )

    def _category_action(request: Request, conn, action, next: str = ""):
        try:
            action()
        except cat.CategoryError as e:
            return _categories(request, conn, error=str(e))
        return _back(_safe_next(next, "/categories"))

    @app.post("/categories")
    def create_category(request: Request, name: str = Form(...), budget: str = Form(""), conn=Depends(get_db)):
        return _category_action(request, conn, lambda: cat.create_category(conn, name, budget))

    # Before /categories/{category_id}, or "merge" would be read as an id
    @app.post("/categories/merge")
    def merge_categories(request: Request, source_id: int = Form(...), target_id: int = Form(...),
                         conn=Depends(get_db)):
        return _category_action(request, conn, lambda: cat.merge_categories(conn, source_id, target_id))

    @app.post("/categories/{category_id}")
    def update_category(request: Request, category_id: int, name: str = Form(...), budget: str = Form(""),
                        conn=Depends(get_db)):
        def update():
            cat.rename_category(conn, category_id, name)
            cat.set_budget(conn, category_id, budget)
        return _category_action(request, conn, update)

    @app.post("/categories/{category_id}/delete")
    def delete_category(category_id: int, conn=Depends(get_db)):
        cat.delete_category(conn, category_id)
        return _back("/categories")

    @app.post("/rules")
    def add_rule(request: Request, pattern: str = Form(...), category_id: int = Form(...), next: str = Form(""),
                 conn=Depends(get_db)):
        if request.headers.get("HX-Request"):
            try:
                cat.add_rule(conn, pattern, category_id)
                message = f"Listo: lo que diga «{pattern.strip().upper()}» quedará en esa categoría."
            except cat.CategoryError as e:
                message = str(e)
            return Response(f'<span class="muted">{Markup.escape(message)}</span>', media_type="text/html")
        return _category_action(request, conn, lambda: cat.add_rule(conn, pattern, category_id), next)

    @app.post("/rules/{rule_id}/delete")
    def delete_rule(rule_id: int, conn=Depends(get_db)):
        cat.delete_rule(conn, rule_id)
        return _back("/categories")

    # --- Installments (12) and subscriptions (15) ----------------------------------------

    @app.get("/installments")
    def installments_page(request: Request, conn=Depends(get_db)):
        movements = history.load_movements(conn)
        plans = installment_plans(movements)
        projections = {}
        for currency in sorted(plans["Currency"].unique()):
            points = projection(plans, currency)
            fmt = lambda value, c=currency: format_amount(value, c)
            projections[currency] = Markup(charts.columns(
                [(month_name(m, short=True), float(a), month_name(m)) for m, a in zip(points["Month"], points["Amount"])],
                fmt, lambda value, c=currency: compact_amount(value, c), tick_every=2,
            ))
        return render(request, "installments.html", active="installments", plans=plans.to_dict("records"),
                      summary=summary(plans), projections=projections)

    @app.get("/subscriptions")
    def subscriptions_page(request: Request, conn=Depends(get_db)):
        subscriptions = detect_subscriptions(history.load_movements(conn))
        totals = {}
        for s in subscriptions:
            totals[s.currency] = totals.get(s.currency, 0) + s.amount
        return render(request, "subscriptions.html", active="subscriptions", subscriptions=subscriptions,
                      totals=totals)

    return app
