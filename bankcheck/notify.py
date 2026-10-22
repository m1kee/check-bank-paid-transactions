"""
Push notifications through ntfy (proposal 20), off unless BANKCHECK_NTFY_URL is set.

ntfy (https://ntfy.sh) is free: install its app, subscribe to a topic with a
long, hard-to-guess name and set BANKCHECK_NTFY_URL=https://ntfy.sh/<topic>.
Anyone who knows the topic can read it, so by default messages only carry the
summary (how many purchases, totals), never the merchants; BANKCHECK_NOTIFY_DETAILS=1
adds them. A self-hosted ntfy server works the same.

After each upload the app sends the pending summary, plus, once each: budgets
that pass 80% or 100% (proposal 30) and alerts about duplicates or unusual amounts.
"""
import datetime
import json
import logging
import os
import sqlite3
import urllib.error
import urllib.request
from dataclasses import dataclass
from urllib.parse import urlsplit

import pandas as pd

from bankcheck import alerts, billing, history, reconcile
from bankcheck import categories as cat
from bankcheck.analysis import analyze
from bankcheck.export import pending_text
from bankcheck.formatting import CURRENCY_NAMES, format_amount
from bankcheck.insights import month_name

log = logging.getLogger(__name__)

TIMEOUT_SECONDS = 5
BUDGET_LEVELS = (1.0, cat.BUDGET_WARNING_RATIO)  # highest first
ALERT_KINDS = (alerts.DUPLICATE, alerts.UNUSUAL)


@dataclass(frozen=True)
class Message:
    title: str
    body: str
    key: str = None  # set for messages sent only once
    tags: tuple = ()
    priority: int = 3


@dataclass(frozen=True)
class NtfySettings:
    url: str = None
    token: str = None
    details: bool = False

    @classmethod
    def from_env(cls) -> "NtfySettings":
        return cls(
            url=os.environ.get("BANKCHECK_NTFY_URL") or None,
            token=os.environ.get("BANKCHECK_NTFY_TOKEN") or None,
            details=os.environ.get("BANKCHECK_NOTIFY_DETAILS", "").lower() in ("1", "true", "si", "sí", "yes"),
        )

    @property
    def enabled(self) -> bool:
        return bool(self.url)

    @property
    def server_and_topic(self):
        """"https://ntfy.sh/mi-tema" -> ("https://ntfy.sh", "mi-tema")."""
        parts = urlsplit(self.url)
        base_path, _, topic = parts.path.rstrip("/").rpartition("/")
        return f"{parts.scheme}://{parts.netloc}{base_path}", topic


def send(settings: NtfySettings, message: Message) -> bool:
    """Publish one message; True if ntfy accepted it. Never raises: a failed notification must not break an upload."""
    if not settings.enabled:
        return False
    server, topic = settings.server_and_topic
    payload = {"topic": topic, "title": message.title, "message": message.body, "priority": message.priority}
    if message.tags:
        payload["tags"] = list(message.tags)
    request = urllib.request.Request(
        server + "/", data=json.dumps(payload).encode("utf-8"), method="POST",
        headers={"Content-Type": "application/json"},
    )
    if settings.token:
        request.add_header("Authorization", f"Bearer {settings.token}")
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return 200 <= response.status < 300
    except (urllib.error.URLError, OSError, ValueError) as e:
        log.warning("No se pudo enviar la notificación: %s", e)
        return False


# --- Messages --------------------------------------------------------------------


def pending_summary(results: list, today: datetime.date = None, details: bool = False, upcoming: list = ()) -> Message:
    """
    🧾 3 compras sin pagar · $27.950 · la más antigua tiene 12 días
    For a currency paid by statement balance, the next statement's total instead (`upcoming`).
    """
    today = pd.Timestamp(today or datetime.date.today())
    by_statement = {u.currency: u for u in upcoming}
    lines = []
    for u in upcoming:
        if u.count:
            prefix = f"{CURRENCY_NAMES.get(u.currency, u.currency)}: " if len(results) > 1 else ""
            lines.append(f"{prefix}próxima facturación {format_amount(u.amount, u.currency)} "
                         f"({u.count} {'compra' if u.count == 1 else 'compras'})")
    for result in results:
        if result.unpaid.empty or result.currency in by_statement:
            continue
        count = len(result.unpaid)
        oldest = (today - result.unpaid["Date"].min()).days
        prefix = f"{CURRENCY_NAMES.get(result.currency, result.currency)}: " if len(results) > 1 else ""
        lines.append(
            f"{prefix}{count} {'compra' if count == 1 else 'compras'} sin pagar · "
            f"{format_amount(result.total_unpaid, result.currency)} · la más antigua tiene {oldest} "
            f"{'día' if oldest == 1 else 'días'}"
        )
    if not lines:
        return Message("✅ Todo pagado", "No hay compras sin pago.", tags=("white_check_mark",))
    body = "\n".join(lines)
    if details:
        body += "\n\n" + pending_text(results, today.date())
    return Message("🧾 Compras sin pagar", body, tags=("receipt",))


def budget_messages(lines: list, month: pd.Period) -> list:
    """One message per budget past 80% or 100% this month (the highest level reached)."""
    messages = []
    for line in lines:
        level = next((lvl for lvl in BUDGET_LEVELS if line.ratio >= lvl), None)
        if level is None:
            continue
        over = level >= 1
        messages.append(Message(
            title=f"{'⛔' if over else '⚠️'} Presupuesto de {line.category}",
            body=(f"Superaste el presupuesto de {month_name(month)}" if over
                  else f"Llevas el {line.ratio:.0%} del presupuesto de {month_name(month)}")
                 + f": {format_amount(line.spent)} de {format_amount(line.budget)}.",
            key=f"budget:{line.category}:{month}:{int(level * 100)}",
            tags=("warning",), priority=4 if over else 3,
        ))
    return messages


def alert_messages(found: list, details: bool = False) -> list:
    messages = []
    for alert in found:
        if alert.kind not in ALERT_KINDS:
            continue
        row = alert.movements[-1]
        ids = ",".join(str(m.get("Id", m["Description"])) for m in alert.movements)
        body = f"{alert.detail} {format_amount(row['Amount'], row['Currency'])} el {row['Date']:%d/%m}."
        if details:
            body = f"{row['Description']}: {body}"
        messages.append(Message(f"⚠️ {alert.label}", body, key=f"alert:{alert.kind}:{ids}", tags=("warning",)))
    return messages


# --- After an upload -------------------------------------------------------------


def _already_sent(conn: sqlite3.Connection, key: str) -> bool:
    return conn.execute("SELECT 1 FROM notifications WHERE key = ?", (key,)).fetchone() is not None


def _mark_sent(conn: sqlite3.Connection, key: str):
    with conn:
        conn.execute(
            "INSERT OR IGNORE INTO notifications (key, sent_at) VALUES (?, ?)",
            (key, datetime.datetime.now().isoformat(timespec="seconds")),
        )


def messages_after_import(conn: sqlite3.Connection, settings: NtfySettings, today: datetime.date = None) -> list:
    """The summary plus the budget and alert messages not sent before."""
    movements = history.load_movements(conn)
    if movements.empty:
        return []
    results = analyze(movements, resolutions=reconcile.load_resolutions(conn), dismissed=reconcile.load_dismissed(conn))
    month = pd.Period(today or datetime.date.today(), freq="M")
    categorized = cat.with_categories(movements, cat.load_rules(conn), cat.load_overrides(conn))
    lines = cat.budget_lines(cat.list_categories(conn), cat.spending(categorized, month), month, today)

    once = budget_messages(lines, month) + alert_messages(alerts.find_alerts(movements), settings.details)
    upcoming = billing.load_upcoming(conn, movements)
    return [pending_summary(results, today, settings.details, upcoming)] + [
        m for m in once if not _already_sent(conn, m.key)
    ]


def notify_after_import(conn: sqlite3.Connection, settings: NtfySettings, today: datetime.date = None) -> int:
    """Send what's due after an upload; returns how many messages ntfy accepted."""
    if not settings.enabled:
        return 0
    sent = 0
    for message in messages_after_import(conn, settings, today):
        if send(settings, message):
            sent += 1
            if message.key:
                _mark_sent(conn, message.key)
    return sent


def sample_message() -> Message:
    return Message("🔔 bankcheck", "Las notificaciones funcionan.", tags=("bell",))

