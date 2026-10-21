# 18 · Movimientos en dólares (USD)

**Categoría:** Conciliación · **Fase:** 2 · **Esfuerzo:** M

## Contexto
En el banco, la misma vista de movimientos tiene **dos tablas**: pesos y dólares. Se descargan **por separado** y la de dólares puede tener otro formato (filas de encabezado, columnas, separador decimal).

## Problema
Hoy el script solo entiende el archivo en pesos. Si se le pasara el de dólares:
- `ROWS_TO_SKIP` y `RAW_COLUMN_INDICES` probablemente no coinciden.
- `safe_to_int` trunca decimales (US$ 9,99 → 9).
- `format_clp` muestra los montos como si fueran pesos.

## Propuesta
1. **Un perfil de formato por tabla** ([17](17-perfiles-de-formato.md)): `clp` y `usd`, cada uno con sus filas de encabezado, columnas y tipo de monto (entero vs decimal). El script detecta cuál es cuál, o se fuerza con `--currency usd`.
2. **Agregar una columna `Currency`** al normalizar, para que el resto del pipeline sepa con qué está trabajando.
3. **Conciliar cada moneda por separado:** una compra en USD solo se empareja con un pago en USD.
4. **Reporte:** una sección por moneda, cada una con sus totales y su formato (`$23.450` vs `US$ 9,99`). Opcionalmente, un total de referencia en CLP con el dólar del día (API pública, ej. mindicador.cl).
5. **Procesar ambos archivos juntos** ([08](08-procesamiento-por-lotes.md)): `python main.py pesos.xls dolares.xls` genera un solo reporte.

## Lo que hay que averiguar primero
- ¿Cómo aparece el pago de la deuda en dólares? ¿En la tabla USD como abono en USD, o en la de pesos como un pago en CLP? Si es lo segundo, el matching 1 a 1 por monto no aplica y habría que conciliar por **saldo** en vez de por compra.

## Criterios de aceptación
- [ ] El archivo USD se procesa sin tocar la configuración del de pesos.
- [ ] Los montos en USD conservan sus decimales.
- [ ] Nunca se empareja una compra en USD con un pago en CLP.
