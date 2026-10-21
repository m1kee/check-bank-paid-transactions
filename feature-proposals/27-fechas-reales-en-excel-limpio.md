# 27 · Guardar fechas reales en el Excel limpio

**Categoría:** Bug menor / Calidad · **Fase:** 0 · **Esfuerzo:** XS

## Problema
`safe_to_datetime` convierte las fechas a **texto** `DD/MM/YYYY` antes de guardar el `.xlsx`. Luego `analysis.py` tiene que volver a parsearlas con `dayfirst=True`. Consecuencias:
- En Excel la columna `Date` no se puede ordenar ni filtrar como fecha.
- El `dropna(subset=['Date'])` corre **antes** de la conversión. Las fechas que no se pudieron leer pasan el filtro, quedan como celdas vacías en el Excel y llegan al análisis como `NaT`: con `--start-date` desaparecen sin aviso, y sin él se cuelan con fecha vacía en el reporte.

## Propuesta
- Guardar `datetime` real en el Excel (openpyxl lo escribe como fecha nativa) y dar formato visual con `number_format = "DD/MM/YYYY"`.
- Hacer el `dropna(subset=['Date'])` **después** de convertir, y avisar cuántas filas se descartaron.

## Criterios de aceptación
- [ ] La columna Date del Excel limpio es de tipo fecha.
- [ ] Las filas con fecha ilegible se descartan con aviso en vez de perderse en silencio.
