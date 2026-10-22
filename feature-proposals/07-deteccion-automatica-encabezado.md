# 07 · Detectar el encabezado automáticamente

**Categoría:** Robustez · **Fase:** 0 · **Esfuerzo:** S

## Problema
`ROWS_TO_SKIP = 18` y `RAW_COLUMN_INDICES = [1, 2, 4, 6, 7, 8, 10]` son "números mágicos". Si el banco agrega una fila de metadatos o una columna, el script lee basura **sin dar error**: los montos quedan en 0 (por `fillna(0)`) y el reporte sale "todo en orden".

## Propuesta
1. Leer el archivo sin `skiprows` y buscar la fila que contiene los encabezados conocidos (ej. "Fecha", "Descripción", "Monto").
2. Mapear las columnas **por nombre** en vez de por índice:
   ```python
   RAW_COLUMN_MAP = {
       "Fecha": "Date",
       "Descripción": "Description",
       "Monto": "Amount ($)",
       ...
   }
   ```
3. Si no encuentra el encabezado, fallar con un error claro.

## Validaciones extra (baratas y muy útiles)
- Abortar si más del X% de los montos quedan en 0 o las fechas en `NaT` tras la conversión.
- Imprimir el rango de fechas y la cantidad de movimientos leídos, para comparar con lo que muestra el banco.

## Archivos a tocar
- `preprocessing.py`, `config.py`.

## Criterios de aceptación
- [ ] Un archivo con una fila extra arriba se procesa igual.
- [ ] Un archivo con columnas cambiadas da un error explicativo, no un reporte vacío.
