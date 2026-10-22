# AGENTS.md

Guía para agentes de IA (y personas) que trabajen en este repo.

## Proyecto
Herramienta que lee la **vista de movimientos del período en curso** del banco (no la cartola), en pesos y dólares, y encuentra compras de 1 cuota sin pago asociado. El roadmap está en `feature-proposals/README.md`.

## Comandos
```bash
uv sync                                  # instalar / actualizar el entorno
uv run bankcheck <archivo.xls> [...]     # correr la CLI
uv run bankcheck-web --reload            # app web en http://127.0.0.1:8000
uv run python -m unittest -v             # tests
```

## Convenciones
- El código, los identificadores y los comentarios van en inglés. Los mensajes al usuario (consola, reporte HTML) van en español.
- La lógica va en `bankcheck/` y no hace `print`. La CLI (`bankcheck/cli.py`) y la app web (`bankcheck/web/`) solo orquestan y muestran.
- Commits con [Conventional Commits](https://www.conventionalcommits.org/es/): `feat:`, `fix:`, `docs:`, `chore:`, `test:`, `refactor:`, `perf:`, `ci:`. Para un cambio incompatible, `feat!:` o un pie `BREAKING CHANGE:`.
- **Nunca** commitear datos bancarios reales (`pre-process-data/`, `data/`, `processed-archive/`, `reports/` están en `.gitignore`). Los tests usan datos inventados (`tests/helpers.py`).

## Versionado: obligatorio en cada PR
La versión vive **solo** en `pyproject.toml` y sigue [SemVer](https://semver.org/lang/es/). **Todo PR que cambie el comportamiento debe subir la versión** según el cambio de mayor impacto que incluya:

| Cambio en el PR | Bump | Ejemplo |
|---|---|---|
| Incompatible: cambia el formato del Excel limpio, los argumentos de la CLI o la configuración de forma que rompe el uso existente | **major** (`uv version --bump major`) | 1.4.2 → 2.0.0 |
| Funcionalidad nueva (`feat:`) | **minor** (`uv version --bump minor`) | 1.4.2 → 1.5.0 |
| Solo arreglos (`fix:`, `perf:`) | **patch** (`uv version --bump patch`) | 1.4.2 → 1.4.3 |
| Sin cambio de comportamiento (`docs:`, `test:`, `ci:`, `chore:`, `refactor:`) | ninguno | — |

**Mientras la versión sea 0.x**, un cambio incompatible sube la **minor** (0.2.0 → 0.3.0), no la major.

Pasos, dentro del mismo PR:
1. `uv version --bump <major|minor|patch>`. Esto también actualiza `uv.lock`.
2. En `CHANGELOG.md`, mover lo de `## [Unreleased]` a `## [X.Y.Z] - AAAA-MM-DD`, dejar `[Unreleased]` vacío y actualizar los links de comparación al final del archivo.
3. `uv run python -m unittest`. **Todo bump de versión debe tener entradas en el CHANGELOG**: `tests/test_version.py` (que corre en el CI) falla si la sección de la versión actual
   - no existe o no tiene fecha (`## [X.Y.Z] - AAAA-MM-DD`),
   - no tiene al menos una entrada `- ...` bajo `### Added`, `Changed`, `Deprecated`, `Removed`, `Fixed` o `Security` (otros subtítulos tampoco se aceptan),
   - o no tiene su link `[X.Y.Z]: https://...` al final del archivo.
4. El título del PR sigue Conventional Commits, y la descripción indica el bump y por qué.

Mientras se trabaja, los cambios se anotan en `## [Unreleased]` del `CHANGELOG.md`, con el formato [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/): Added / Changed / Fixed / Removed.

## Release
Después de hacer merge del PR a `main`:
```bash
git checkout main && git pull
git tag -a vX.Y.Z -m "vX.Y.Z"
git push origin vX.Y.Z
```
