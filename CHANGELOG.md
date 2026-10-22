# Changelog

Todos los cambios relevantes del proyecto se documentan en este archivo.

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y el proyecto usa [Versionado Semántico](https://semver.org/lang/es/). La versión vive en `pyproject.toml`.

## [Unreleased]

## [0.10.0] - 2026-10-22

### Added
- Subir movimientos: se pueden arrastrar los archivos .xls / .xlsx a la zona de subida. Mientras se arrastra, la zona se destaca, se muestran los archivos elegidos y se descartan los que no son .xls / .xlsx. Si se suelta un archivo fuera de la zona, el navegador ya no lo abre ni sale de la página. Sin JavaScript se puede seguir haciendo clic para elegir los archivos.

### Changed
- Los botones "Subir descarga" pasan a llamarse "Subir movimientos", igual que la página, y los textos que invitan a subir hablan de los movimientos no facturados del banco.

## [0.9.1] - 2026-10-22

### Fixed
- Un movimiento que el banco muestra primero como provisorio (p. ej. `ARAMCO`, sin ciudad) y después ya contabilizado con otra descripción (`ARAMCO COMPRAS`, con ciudad) quedaba dos veces en el historial. El pago se asignaba a la versión provisoria y la definitiva aparecía como no pagada. Ahora, al importar una descarga, los movimientos anteriores de la misma moneda con fecha dentro de su rango que ya no aparecen en ella se marcan como reemplazados y no se analizan. Se conservan en el historial y vuelven si una descarga posterior los muestra de nuevo (esquema del historial v4).

## [0.9.0] - 2026-10-22

### Added
- Rediseño de la app web como dashboard: barra lateral con íconos (barra superior en el celular), encabezado de página con acciones, tarjetas de indicadores con variación y mini-tendencia, grilla de tarjetas, estados vacíos, tema claro/oscuro con botón (recuerda la elección) y la tipografía Inter incluida en la app.
- Gráficos nuevos en el Resumen: **ritmo del mes** (gasto acumulado día a día vs el mes anterior, con el presupuesto total como referencia), **últimos 12 meses** con el mes elegido destacado, mini-tendencia de 6 meses del gasto y proyección de cuotas.
- Tooltips en todos los gráficos (`static/charts.js`): línea vertical que sigue al cursor en los gráficos de línea y valor por barra. Sin JavaScript se mantienen los tooltips nativos.
- Ejes con valores compactos ($45K, $1,2M) y porcentaje de cada categoría sobre el total.
- Categorías: tendencia de 6 meses por categoría y barra de presupuesto en la tabla.
- Suscripciones: tendencia del monto de cada cobro. Cuotas: barra de avance por compra.
- Subir: zona para soltar archivos y lista de las últimas descargas importadas.

### Changed
- "Inicio" pasa a llamarse "Resumen".
- Los montos negativos se muestran con el signo antes del símbolo (`-$38.000` en vez de `$-38.000`).

### Fixed
- En modo oscuro, los botones principales tenían poco contraste.

## [0.8.0] - 2026-10-21

### Added
- "Próxima facturación" para los dólares (o cualquier moneda en modo `statement`): el total de las compras de la última descarga, que es la vista de movimientos no facturados del banco, con cuántas compras son, desde qué fecha y de qué descarga sale. Aparece en Inicio, arriba de los dólares en Pendientes y en la notificación después de subir, en lugar de "N compras sin pagar" para esa moneda.

## [0.7.0] - 2026-10-21

### Added
- Notificaciones por [ntfy](https://ntfy.sh), gratis y apagadas por defecto (20): después de cada subida llega el resumen de pendientes, y una sola vez cada aviso de presupuesto al 80 % o 100 % (lo que faltaba de 30) y de cobro duplicado o monto inusual. Por defecto sin comercios (`BANKCHECK_NOTIFY_DETAILS=1` los agrega). Botón de prueba en Subir. Configuración: `BANKCHECK_NTFY_URL`, `BANKCHECK_NTFY_TOKEN`.
- Matching por saldo para los dólares (18): un pago en USD es el total facturado y cubre el bloque continuo de compras pendientes que suma exactamente su monto. Se elige por moneda en `MATCHING_MODE`; los pesos siguen compra a compra.
- Migración v3 del historial: tabla `notifications`.

### Fixed
- El formato de dólares se validó con una descarga real (17, 18) y no era el supuesto: no tiene columnas de cuotas, tiene una columna País y el monto va en la columna 8. Antes, un archivo en dólares se rechazaba con "el encabezado no coincide". Ahora cada compra en dólares cuenta como de un solo cargo y se guarda el país (la "ciudad" del banco trae teléfonos o dominios).
- Los pagos `PAGO DOLAR …` no se reconocían como pagos.

## [0.6.0] - 2026-10-21

Fases 2 y 3 del roadmap, más 06 y 19 de la Fase 4.

### Added
- Conciliación manual (03): marcar una compra como pagada o ignorada con un motivo, o ignorar un pago, desde Pendientes. Se guarda en el historial, se puede deshacer y aparece en "Resueltas a mano".
- Detalle de qué pago cubrió cada compra, con los días que tardó, en la web y en el reporte (04).
- Sugerencias de pagos agrupados (11): un pago sin compra que equivale a la suma de 2 a 4 compras pendientes anteriores se sugiere; si hay varias combinaciones se muestran todas. Nada se aplica solo: se acepta o se descarta.
- Categorías (13): reglas editables (gana la más larga; sin importar mayúsculas ni tildes), con las de `config.DEFAULT_CATEGORIES` como punto de partida. En Movimientos se cambia la categoría de cada fila y la app ofrece crear la regla. Página Categorías: crear, renombrar, borrar y unir categorías, y la lista de comercios sin categoría.
- Presupuestos mensuales por categoría (30), con barra de avance y marca de cuánto del mes ha pasado.
- Inicio con gastos del mes vs el anterior, gasto por día y por categoría, y pendiente por antigüedad (14). Los gráficos son HTML/CSS, sin JavaScript, y también van en el reporte HTML.
- Cuotas vigentes (12): cuotas restantes, deuda restante, mes de término, compromiso mensual y proyección a 12 meses.
- Suscripciones detectadas (15): cobros mensuales por un monto parecido durante 3 meses o más, con costo anual y aviso si el precio subió.
- Alertas "Revisar" (16): posibles cobros duplicados, montos inusuales, y comercios y ciudades nuevos. La sección no aparece si no hay alertas.
- Copiar la lista de pendientes como texto (para WhatsApp) y descargarla como CSV, en la web y en el reporte; `--export` en la CLI (19).
- CLI: `--no-open`, `--no-archive`, `--dry-run`, `-e/--end-date` y `--reanalyze` (06).
- CLI: sin archivos procesa todas las descargas de `pre-process-data/` (08).
- Migración v2 del historial: tablas `resolutions`, `dismissed_suggestions`, `categories` y `category_rules`, y columna `movements.category_id`. Se aplica sola al abrir un historial existente.

### Changed
- La página de inicio de la web pasa a ser Inicio (`/dashboard`); Pendientes sigue en `/pending`.
- En el celular, la tabla de Movimientos se muestra como una tarjeta por movimiento.
- La CLI sin archivos y sin `--db` ya no es un error de uso: busca descargas en `pre-process-data/` y, si no hay ninguna, termina con código 1.
- El pie del reporte HTML dice "bankcheck" en vez de "Account Analysis Tool".

## [0.5.0] - 2026-10-21

### Added
- `-v/--verbose` y `-q/--quiet` en la CLI (24).
- `Dockerfile` y `docker-compose.yml` para correr la app web en un contenedor, con los datos en un volumen, contraseña obligatoria y el puerto publicado solo en `127.0.0.1` por defecto (26).
- Variable de entorno `BANKCHECK_DATA_DIR` para elegir la carpeta de datos (archivos limpios, historial y subidas) sin depender del directorio actual (26).
- El CI también construye la imagen de Docker.
- La app web registra cada importación en su log.

### Changed
- Los mensajes de avance de la CLI usan `logging` y salen por stderr; el reporte sale por stdout, así que se puede redirigir a un archivo (24).
- El encabezado de la CLI pasa de "Account Analysis Tool" a "bankcheck vX.Y.Z · análisis de movimientos", y se quitó "Proceso completo.".
- Los errores se propagan como excepciones y `main()` devuelve el código de salida; un historial de una versión más nueva también termina con código 1 (24).

### Fixed
- Si el historial no se podía migrar, la conexión quedaba abierta y el archivo bloqueado.

## [0.4.0] - 2026-10-21

### Added
- App web (MVP de la propuesta 22) con FastAPI, Jinja2 y HTMX, pensada primero para el celular: `uv run bankcheck-web`.
- Página **Subir**: importa una o varias descargas al historial y muestra cuántos movimientos eran nuevos. Si un archivo no se puede leer, no se importa ninguno. Los originales se guardan en `data/uploads/`.
- Página **Pendientes**: compras sin pago de todo el historial, con totales, antigüedad y filtro por fecha de inicio, más los pagos sin compra asociada.
- Página **Movimientos**: todo el historial con buscador y filtros por moneda y fechas.
- Contraseña opcional (`BANKCHECK_PASSWORD`) y rutas configurables (`BANKCHECK_DB`, `BANKCHECK_UPLOADS_DIR`).

## [0.3.0] - 2026-10-21

### Added
- Historial persistente en SQLite (`bankcheck/history.py`): cada descarga se importa una vez y los movimientos repetidos solo se marcan como vistos de nuevo. Guarda cuándo se vio cada movimiento por primera y última vez, y un registro de cada importación (09).
- `--db [RUTA]` en la CLI: importa los archivos al historial (por defecto `data/bank.db`) y analiza todo el historial. Una compra impaga sigue pendiente después del cierre del período, y un pago del período siguiente puede cubrirla. Sin archivos, solo vuelve a analizar el historial.
- El esquema de la base se versiona y se migra solo al abrirla.

## [0.2.0] - 2026-10-21

Fase 0 del roadmap (`feature-proposals/`): base de lógica reutilizable, sin UI.

### Added
- Paquete `bankcheck/` con el núcleo separado de la CLI, para que la futura app web use la misma lógica (propuesta 29).
- Detección automática del encabezado y de la sección del archivo ("Movimientos Nacionales" / "Movimientos Internacionales"); ya no depende de un número fijo de filas a saltar (07).
- Perfiles de formato por moneda y columna `Currency`; soporte inicial para dólares, aún no validado con un archivo real (17, 18).
- Se pueden pasar varios archivos a la vez; los movimientos repetidos entre descargas se cuentan una sola vez (10).
- Sección "Pagos sin compra asociada" en la consola y en el reporte HTML.
- `--version` en la CLI y versión en el pie del reporte.
- Suite de tests con datos inventados y CI en GitHub Actions (23).
- `CHANGELOG.md`, y tests que obligan a que cada versión de `pyproject.toml` tenga aquí una sección con fecha, al menos una entrada y su link de comparación.
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

[Unreleased]: https://github.com/m1kee/check-bank-paid-transactions/compare/v0.10.0...HEAD
[0.10.0]: https://github.com/m1kee/check-bank-paid-transactions/compare/v0.9.1...v0.10.0
[0.9.1]: https://github.com/m1kee/check-bank-paid-transactions/compare/v0.9.0...v0.9.1
[0.9.0]: https://github.com/m1kee/check-bank-paid-transactions/compare/v0.8.0...v0.9.0
[0.8.0]: https://github.com/m1kee/check-bank-paid-transactions/compare/v0.7.0...v0.8.0
[0.7.0]: https://github.com/m1kee/check-bank-paid-transactions/compare/v0.6.0...v0.7.0
[0.6.0]: https://github.com/m1kee/check-bank-paid-transactions/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/m1kee/check-bank-paid-transactions/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/m1kee/check-bank-paid-transactions/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/m1kee/check-bank-paid-transactions/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/m1kee/check-bank-paid-transactions/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/m1kee/check-bank-paid-transactions/releases/tag/v0.1.0
