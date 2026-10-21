# 04 · Mostrar qué pago cubrió cada compra

**Categoría:** Reporte · **Fase:** 2 · **Esfuerzo:** S

## Problema
El reporte solo muestra lo que **no** cuadró. Si el algoritmo empareja mal (ver [01](01-matching-con-fechas.md)), no hay forma de darse cuenta: una compra pendiente puede quedar "pagada" por un pago que no le corresponde y desaparecer del reporte en silencio.

## Propuesta
Que el matching devuelva también los pares `(compra, pago)` y que el reporte HTML tenga una segunda tabla, colapsable:

| Compra | Fecha compra | Monto | Pago | Fecha pago | Días |
|---|---|---|---|---|---|
| UBER TRIP | 03/10 | $4.500 | PAGO ONLINE | 05/10 | 2 |

Incluir también la lista de **pagos huérfanos** (pagos sin compra asociada), que suele delatar errores.

## Por qué vale la pena
Es la diferencia entre confiar ciegamente en el número final y poder **auditarlo** en 10 segundos.

## Archivos a tocar
- `analysis.py` (guardar los pares al emparejar), `html_reporter.py` (sección `<details>`).

## Criterios de aceptación
- [ ] Cada compra pagada aparece con el pago que la cubrió.
- [ ] Los pagos huérfanos aparecen listados.
