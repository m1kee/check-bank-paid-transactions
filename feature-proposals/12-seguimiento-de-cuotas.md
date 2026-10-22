# 12 · Seguimiento de compras en cuotas

**Categoría:** Nuevo análisis · **Fase:** 3 · **Esfuerzo:** M

## Problema
El análisis descarta todo lo que no sea `01/01`. Las compras en cuotas (`03/12`, etc.) quedan fuera, y son justamente las que comprometen plata a futuro.

## Propuesta
Una sección nueva en el reporte, **"Cuotas vigentes"**:

| Compra | Cuota actual | Valor cuota | Cuotas restantes | Deuda restante | Termina |
|---|---|---|---|---|---|
| NOTEBOOK | 03/12 | $45.000 | 9 | $405.000 | jul 2027 |

Y un total: **"Compromiso mensual en cuotas: $X"** y **"Deuda total en cuotas: $Y"**.

## Cómo
- Parsear `Installments` con `r"(\d+)/(\d+)"`.
- Agrupar por descripción + valor de cuota para no contar dos veces la misma compra.
- Proyectar mes a mes cuánto baja la carga de cuotas (gráfico de barras, ver [14](14-dashboard-con-graficos.md)).

## Criterios de aceptación
- [ ] Una compra `03/12` de $45.000 muestra 9 cuotas y $405.000 restantes.
- [ ] El total mensual coincide con la suma de cuotas vigentes.
