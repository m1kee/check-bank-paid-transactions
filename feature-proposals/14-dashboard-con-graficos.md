# 14 · Gráficos en el reporte HTML

**Categoría:** Reporte · **Fase:** 3 · **Esfuerzo:** M

## Problema
El reporte tiene tarjetas con totales y una tabla. Sirve para "¿qué falta pagar?", pero no para ver tendencias.

## Propuesta
Agregar al HTML (sin servidor; con SVG generado en Python o con una librería JS embebida):
1. **Gasto por día/semana** del período (barras).
2. **Gasto por categoría** ([13](13-categorizacion-de-gastos.md)) (barras horizontales; mejor que un gráfico de torta).
3. **Pendiente por antigüedad**: cuánto lleva 0–7, 8–30 y +30 días sin pagar.
4. **Comparación con el mes anterior** (necesita [09](09-historial-sqlite.md)).

## Detalles
- Mantener el reporte autocontenido: un solo archivo `.html` que funcione offline.
- Respetar el tema oscuro actual.

## Criterios de aceptación
- [ ] El reporte se abre sin conexión y muestra los gráficos.
