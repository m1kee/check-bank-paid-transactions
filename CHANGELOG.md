# Changelog

Todos los cambios relevantes del proyecto se documentan en este archivo.

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y el proyecto usa [Versionado Semántico](https://semver.org/lang/es/). La versión vive en `pyproject.toml`.

## [Unreleased]

## [0.2.0] - 2026-10-21

Fase 0 del roadmap (`feature-proposals/`): base de lógica reutilizable, sin UI.

### Added
- Paquete `bankcheck/` con el núcleo separado de la CLI, para que la futura app web use la misma lógica (propuesta 29).
- Detección automática del encabezado y de la sección del archivo ("Movimientos Nacionales" / "Movimientos Internacionales"); ya no depende de un número fijo de filas a saltar (07).
- Perfiles de formato por moneda y columna `Currency`; soporte inicial para dólares, aún no validado con un archivo real (17, 18).
- Se pueden pasar varios archivos a la vez; los movimientos repetidos entre descargas se cuentan una sola vez (10).
- Sección "Pagos sin compra asociada" en la consola y en el reporte HTML.
- `--version` en la CLI y versión en el pie del reporte.
- Suite de tests con datos inventados (41 tests) y CI en GitHub Actions (23).
- `CHANGELOG.md`, y un test que falla si la versión de `pyproject.toml` no tiene su entrada aquí.
- `AGENTS.md` (importado desde `CLAUDE.md`) con las convenciones del repo y la regla de subir la versión en cada PR.
- `pyproject.toml` y `uv.lock`: el proyecto se instala con [uv](https://docs.astral.sh/uv/) y la CLI queda como el comando `bankcheck` (26).

### Changed
- El matching respeta las fechas: un pago solo cubre compras del mismo monto hechas antes (o el mismo día), dentro de una ventana de 45 días, y los montos repetidos se pagan de la más antigua a la más nueva (01). Configurable con `MATCH_WINDOW_DAYS` y `PAYMENT_EARLY_TOLERANCE_DAYS`.
- Las exclusiones de pagos (p. ej. `COMERCIALSANA`) se configuran en `PAYMENT_EXCLUSIONS` en vez de estar en el código (02).
- El Excel limpio guarda fechas reales, con formato `DD/MM/YYYY` (27).
- La columna de monto pasa de `Amount ($)` a `Amount`.
- La CLI se ejecuta con `uv run bankcheck <archivos>` en vez de `python main.py <archivo>`.
- Dependencias actualizadas: pandas 3, numpy 2, openpyxl 3.1.5, xlrd 2.0.2. Python 3.12 o superior.
- Mensajes de consola en español.
- Se leen todos los archivos antes de archivar ninguno: si uno falla, no se mueve nada.
- La CLI termina con código de salida 1 cuando no puede leer un archivo.

### Fixed
- Un pago anterior a una compra podía darla por pagada (p. ej. el pago de una suscripción del mes anterior "pagaba" el cobro de este mes).
- El reporte HTML no escapaba las descripciones de los comercios (05).
- Las ciudades vacías aparecían como `nan`.
- Un cambio de formato del banco podía producir un reporte "todo en orden" con datos mal leídos; ahora falla con un error explicativo.

### Removed
- El reporte HTML ya no carga la fuente desde Google Fonts: funciona sin conexión.
- `requirements.txt` (reemplazado por `pyproject.toml` + `uv.lock`) y `main.py` (ahora `bankcheck/cli.py`).

## [0.1.0] - 2026-10-21

Versión inicial, tal como estaba en `main` antes de versionar.

### Added
- Lectura y limpieza del `.xls` del banco y archivo limpio en `.xlsx`.
- Matching 1 a 1 por monto entre compras de 1 cuota y pagos.
- Archivado del archivo original con timestamp.
- Filtro opcional por fecha de inicio (`--start-date`).
- Reporte HTML en modo oscuro que se abre en el navegador.
- Detección de pagos por `PAGO PESOS TAR`, `PAGO PESOS TEF`, `PAGO ONLINE` y `MERCADOPAGO`.

[Unreleased]: https://github.com/m1kee/check-bank-paid-transactions/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/m1kee/check-bank-paid-transactions/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/m1kee/check-bank-paid-transactions/releases/tag/v0.1.0
