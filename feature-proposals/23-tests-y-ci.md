# 23 · Más tests y CI

**Categoría:** Calidad · **Fase:** 0 · **Esfuerzo:** M

## Problema
Hay 2 tests y cubren solo `is_payment_description`. La lógica más delicada (el matching) y el preprocesamiento no tienen tests, así que cualquier cambio de los que se proponen aquí es arriesgado.

## Propuesta
1. **Refactor mínimo para poder testear:** separar en `analysis.py` la lógica pura (`match_payments(df) -> resultado`) de la lectura del archivo y los `print`.
2. **Fixtures anonimizadas:** un archivo de movimientos falso (pesos y dólares) en `tests/fixtures/` con el mismo formato que la real (montos y comercios inventados).
3. **Casos a cubrir:**
   - Matching: montos repetidos, pagos huérfanos, filtro por fecha, archivo vacío.
   - Preprocesamiento: filas sin fecha, montos con formato raro, columnas faltantes.
   - Reporte: escapado de HTML ([05](05-escapar-html.md)), estado vacío.
4. **CI:** GitHub Actions que corra `python -m unittest` (o `pytest`) en cada push.

## Por qué antes que lo demás
Es la red de seguridad para [01](01-matching-con-fechas.md), [07](07-deteccion-automatica-encabezado.md) y [09](09-historial-sqlite.md).

## Criterios de aceptación
- [ ] El matching tiene tests para cada caso borde listado.
- [ ] El CI corre en cada push y bloquea si falla.
- [ ] Ningún dato bancario real en el repo.
