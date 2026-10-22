# 30 · Presupuestos por categoría

**Categoría:** Análisis · **Fase:** 3 · **Esfuerzo:** S–M

## Problema
Saber en qué se gastó ([13](13-categorizacion-de-gastos.md)) sirve, pero ayuda más saber **a mitad de mes** si vas bien o te estás pasando.

## Propuesta
- Definir un presupuesto mensual por categoría desde la app web ([22](22-app-web.md)): Supermercado $250.000, Delivery $60.000, etc.
- En el inicio, una barra por categoría: gastado vs presupuesto, y una marca que indica **cuánto del mes ha pasado**. Si la barra va más adelante que la marca, vas por sobre el ritmo.
  ```
  Delivery     ███████████░░░░  $48.000 / $60.000   ▲ hoy (día 21 de 31)
  ```
- Alerta ([20](20-notificaciones.md)) cuando una categoría supera el 80% o el 100%.
- Los presupuestos se manejan en CLP. Si se convierten los gastos en USD, se suman con el dólar del día como referencia ([18](18-multi-moneda.md)).

## Criterios de aceptación
- [x] Se puede definir y editar el presupuesto de cada categoría.
- [x] El inicio muestra el avance del mes por categoría.

## Estado (v0.6.0)
Presupuestos en pesos, editables en Categorías. Pendiente: la alerta al 80 % y 100 % (necesita [20](20-notificaciones.md)) y convertir los gastos en dólares.

## Estado (v0.7.0)
Las alertas al 80 % y 100 % llegaron en v0.7.0 por ntfy ([20](20-notificaciones.md)).
