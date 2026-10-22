# 16 · Alertas de cobros duplicados o anómalos

**Categoría:** Nuevo análisis · **Fase:** 3 · **Esfuerzo:** S

## Problema
Los cobros duplicados (mismo comercio, mismo monto, mismo día o con minutos de diferencia) pasan, y en una lista larga de movimientos no se notan.

## Propuesta
Una sección "⚠️ Revisar" en el reporte con:
- **Posibles duplicados:** misma descripción y monto en ≤ 2 días.
- **Montos inusuales:** compras mucho mayores que lo normal en ese comercio (ej. 3× la mediana).
- **Comercios nuevos:** primera vez que aparecen (necesita [09](09-historial-sqlite.md)).
- **Cobros internacionales o en otra ciudad** inesperados (la columna `City` ya existe y no se usa).

## Criterios de aceptación
- [ ] Dos cobros idénticos el mismo día aparecen en "Revisar".
- [ ] La sección no se muestra si no hay alertas.
