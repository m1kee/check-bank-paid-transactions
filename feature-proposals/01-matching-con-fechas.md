# 01 · Matching que respeta fechas

**Categoría:** Lógica de conciliación · **Fase:** 0 · **Esfuerzo:** M

## Problema
Hoy `analyze_movements` empareja compras y pagos solo por **monto** (`Counter` de montos). No mira las fechas, así que:
- Un pago hecho **antes** de la compra puede "pagarla".
- Si hay dos compras de $5.990 (una en marzo y otra en mayo) y un solo pago en abril, el algoritmo marca como pendiente la **última** compra (por el orden de `iterrows`), aunque el pago de abril solo podía corresponder a la de marzo.
- Un pago de $10.000 de otra cosa puede "tapar" una compra de $10.000 que en realidad sigue pendiente.

## Propuesta
Emparejar cada pago con la compra **más antigua del mismo monto que ocurrió antes o el mismo día**, dentro de una ventana configurable (ej. 45 días).

## Cómo funcionaría
1. Ordenar compras y pagos por fecha.
2. Recorrer los pagos en orden cronológico; para cada uno, buscar la compra sin pagar más antigua con el mismo monto y `fecha_compra <= fecha_pago <= fecha_compra + VENTANA`.
3. Lo que quede sin emparejar es lo pendiente. Los pagos que no encontraron compra se reportan aparte como "pagos huérfanos".

```python
# config.py
MATCH_WINDOW_DAYS = 45
```

## Archivos a tocar
- `analysis.py`: reemplazar los pasos 3–5 por una función `match_payments(shopping, payments) -> (matched, unpaid, orphan_payments)`.
- `config.py`: `MATCH_WINDOW_DAYS`.
- `tests/test_analysis.py`: casos con pago anterior a la compra, montos repetidos en meses distintos, pago fuera de ventana.

## Riesgos
- Si el banco registra el pago con una fecha distinta a la real (ej. fecha contable), una ventana muy estricta da falsos pendientes. Por eso la ventana es configurable y conviene permitir unos días de tolerancia "hacia atrás".

## Criterios de aceptación
- [ ] Un pago anterior a la compra no la marca como pagada (salvo tolerancia configurada).
- [ ] Con montos repetidos se marca como pendiente la compra correcta.
- [ ] El reporte lista los pagos huérfanos.
