# 11 · Detectar pagos que cubren varias compras

**Categoría:** Lógica de conciliación · **Fase:** 2 · **Esfuerzo:** M

## Problema
El matching actual es 1 a 1 por monto exacto. Si haces tres compras ($3.000, $4.500 y $2.500) y las pagas juntas con un pago de $10.000, el script reporta **las tres como pendientes** y además un pago de $10.000 que no cuadra con nada.

## Propuesta
Después del matching 1 a 1, intentar cubrir los **pagos huérfanos** con combinaciones de compras pendientes (problema de *subset sum*):
- Solo compras anteriores al pago y dentro de la ventana ([01](01-matching-con-fechas.md)).
- Limitar a combinaciones de hasta N compras (ej. 4) para que sea rápido y no invente coincidencias.
- Si hay **más de una** combinación posible, no decidir: mostrarla como "posible match" para que la confirmes ([03](03-conciliacion-manual.md)).

## Detalles
- Con ~50 compras pendientes y N=4 son unos 230 mil combinaciones: se calcula al instante.
- Opcional: tolerancia de unos pocos pesos por redondeos.

## Riesgos
- Falsos positivos: entre muchas compras siempre hay alguna combinación que suma cualquier número. Por eso conviene presentarlo como **sugerencia**, no como match automático.

## Criterios de aceptación
- [x] Un pago de $10.000 que equivale exactamente a 3 compras pendientes aparece sugerido.
- [x] Las sugerencias ambiguas no se aplican solas.

## Estado (v0.6.0)
Ninguna sugerencia se aplica sola, ni siquiera las que tienen una sola combinación: se aceptan o se descartan en Pendientes. Se prueban hasta 30 compras candidatas por pago (las más cercanas en fecha) y se muestran hasta 5 combinaciones. Tolerancia en `GROUP_MATCH_TOLERANCE`.
