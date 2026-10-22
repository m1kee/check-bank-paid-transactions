"""Run the web app: `uv run bankcheck-web` (or `python -m bankcheck.web`)."""
import argparse

import uvicorn

from bankcheck import __version__


def main():
    parser = argparse.ArgumentParser(
        description="App web de bankcheck. Se configura con las variables de entorno BANKCHECK_DB, "
        "BANKCHECK_UPLOADS_DIR y BANKCHECK_PASSWORD."
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Dirección donde escuchar (por defecto 127.0.0.1; 0.0.0.0 para entrar desde otros equipos).",
    )
    parser.add_argument("--port", type=int, default=8000, help="Puerto (por defecto 8000).")
    parser.add_argument("--reload", action="store_true", help="Reinicia al cambiar el código (desarrollo).")
    args = parser.parse_args()

    uvicorn.run(
        "bankcheck.web.app:create_app", factory=True, host=args.host, port=args.port, reload=args.reload
    )


if __name__ == "__main__":
    main()
