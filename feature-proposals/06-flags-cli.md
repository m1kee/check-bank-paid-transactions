# 06 · Más opciones en la CLI: `--no-open`, `--no-archive`, `--dry-run`, `--end-date`

**Categoría:** Usabilidad · **Fase:** 4 · **Esfuerzo:** S

## Problema
- El script **siempre mueve** el archivo original a `processed-archive/`. Si quieres re-correr el análisis sobre el mismo archivo (por ejemplo, después de ajustar config), tienes que ir a buscarlo y renombrarlo.
- **Siempre abre** el navegador, lo que molesta en pruebas o si lo corres por SSH.
- Solo hay fecha de inicio; no se puede analizar un rango cerrado (ej. solo septiembre).

> Con la app web ([22](22-app-web.md)), la CLI queda como herramienta para desarrollar y probar en local. Estos flags (sobre todo `--no-open` y `--no-archive`) sirven para eso.

## Propuesta
| Flag | Efecto |
|---|---|
| `--no-open` | Genera el HTML pero no abre el navegador |
| `--no-archive` | No mueve el archivo de entrada |
| `--dry-run` | No escribe nada en disco: solo imprime el análisis |
| `-e, --end-date` | Fecha fin del rango (inclusive) |
| `--reanalyze <archivo.xlsx>` | Saltarse el preprocesamiento y analizar un archivo limpio de `data/` |

## Archivos a tocar
- `main.py` (argparse y flujo), `analysis.py` (filtro `end_date`, parámetro `open_browser`), `html_reporter.py`.

## Criterios de aceptación
- [ ] `python main.py x.xls --no-archive --no-open` deja la carpeta igual que antes y no abre nada.
- [ ] `--reanalyze` funciona sobre cualquier archivo de `data/`.
