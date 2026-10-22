"""
Web app: upload the bank's downloads, see unpaid purchases and browse the history.

Pages are rendered server-side with Jinja2; HTMX only refreshes the movements
table while filtering, so every page also works without JavaScript.
"""
import datetime
import hashlib
import os
import re
import secrets
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile, status
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from bankcheck import __version__, config, history
from bankcheck.analysis import analyze
from bankcheck.formatting import CURRENCY_NAMES, format_amount
from bankcheck.parsers import ParseError, parse_file

HERE = Path(__file__).parent

# Rows shown at once in the movements table
MOVEMENTS_PAGE_SIZE = 300


@dataclass
class Settings:
    db_path: str = config.DB_PATH
    uploads_dir: str = config.UPLOADS_FOLDER
    # When set, every page asks for it (HTTP Basic, any user name)
    password: str = None

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            db_path=os.environ.get("BANKCHECK_DB", config.DB_PATH),
            uploads_dir=os.environ.get("BANKCHECK_UPLOADS_DIR", config.UPLOADS_FOLDER),
            password=os.environ.get("BANKCHECK_PASSWORD") or None,
        )


@dataclass
class FileImport:
    name: str
    sections: list
    new_count: int
    existing_count: int
    warnings: list = field(default_factory=list)


def _safe_filename(name: str) -> str:
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(name or "archivo").name).strip("._")
    return stem or "archivo"


def _parse_date(value: str):
    """A YYYY-MM-DD form field; empty or invalid means "no filter"."""
    try:
        return datetime.date.fromisoformat(value) if value else None
    except ValueError:
        return None


def _date(value) -> str:
    return value.strftime("%d/%m/%Y") if pd.notnull(value) else ""


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
    templates.env.globals.update(version=__version__, currency_names=CURRENCY_NAMES)

    def render(request: Request, name: str, **context):
        return templates.TemplateResponse(request, name, context)

    @app.get("/")
    def home():
        return RedirectResponse("/pending", status_code=status.HTTP_303_SEE_OTHER)

    @app.get("/pending")
    def pending(request: Request, start: str = "", conn=Depends(get_db)):
        start = _parse_date(start)
        movements = history.load_movements(conn)
        results = analyze(movements, start_date=start)
        today = pd.Timestamp(datetime.date.today())
        for result in results:
            result.unpaid = result.unpaid.assign(Age=(today - result.unpaid["Date"]).dt.days)
        return render(
            request, "pending.html", active="pending", results=results, start=start,
            has_history=not movements.empty,
        )

    @app.get("/upload")
    def upload_form(request: Request):
        return render(request, "upload.html", active="upload", imports=None, error=None)

    @app.post("/upload")
    def upload(request: Request, files: list[UploadFile] = File(...), conn=Depends(get_db)):
        files = [f for f in files if f.filename]
        if not files:
            return render(request, "upload.html", active="upload", imports=None,
                          error="Elige al menos un archivo.")

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
            for _, path, _ in saved:
                os.remove(path)
            return render(request, "upload.html", active="upload", imports=None,
                          error=f"No se importó nada. {e}")

        imports = []
        for (name, path, sha256), parsed_file in zip(saved, parsed):
            result = history.import_movements(conn, parsed_file.movements, source_name=name, sha256=sha256)
            imports.append(FileImport(name, parsed_file.sections, result.new_count,
                                      result.existing_count, parsed_file.warnings))
        return render(request, "upload.html", active="upload", imports=imports, error=None)

    @app.get("/movements")
    def movements_page(
        request: Request,
        q: str = "",
        currency: str = "",
        date_from: str = "",
        date_to: str = "",
        conn=Depends(get_db),
    ):
        date_from, date_to = _parse_date(date_from), _parse_date(date_to)
        df = history.load_movements(conn, currency=currency or None)
        currencies = [c for c, in conn.execute("SELECT DISTINCT currency FROM movements ORDER BY currency")]
        if q:
            df = df[df["Description"].str.contains(q, case=False, regex=False)]
        if date_from:
            df = df[df["Date"] >= pd.Timestamp(date_from)]
        if date_to:
            df = df[df["Date"] <= pd.Timestamp(date_to)]
        df = df.iloc[::-1]  # newest first

        context = dict(
            active="movements", rows=df.head(MOVEMENTS_PAGE_SIZE).to_dict("records"), total=len(df),
            page_size=MOVEMENTS_PAGE_SIZE, q=q, currency=currency, currencies=currencies,
            date_from=date_from, date_to=date_to,
        )
        # The filter form (HTMX) only needs the table
        is_filter = request.headers.get("HX-Target") == "movements-table"
        name = "_movements_table.html" if is_filter else "movements.html"
        return render(request, name, **context)

    return app
