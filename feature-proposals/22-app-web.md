# 22 · App web en el servidor

**Categoría:** Producto · **Fase:** 1 (MVP) y luego crece · **Esfuerzo:** L

## Objetivo
Que todo se haga desde el navegador, en el Mac, el PC o el celular: subir los movimientos, ver los pendientes, catalogar gastos y ver el dashboard. Corre en el servidor casero ([28](28-servidor-casero.md)) y guarda todo en SQLite ([09](09-historial-sqlite.md)).

## Stack recomendado
- **Backend:** FastAPI, usando el núcleo de [29](29-nucleo-reutilizable.md).
- **Frontend:** plantillas Jinja2 + **HTMX**. Todo queda en Python, sin build de JavaScript, y alcanza para tablas editables, filtros y formularios. Si más adelante quieres una UI más rica o aprender React, se puede migrar el frontend sin tocar el backend.
- **Gráficos:** una librería JS embebida (ej. Chart.js) en las páginas del dashboard.
- **Pensada primero para celular:** la mayoría de las veces se va a usar justo después de descargar los movimientos desde la app del banco.
- **Acceso:** solo vía Tailscale. Igual conviene un login simple (contraseña única) por si el servidor queda accesible por error.

## MVP (Fase 1)
1. **Subir archivo:** botón para subir uno o varios `.xls`. Se detecta solo si es de pesos o dólares ([17](17-perfiles-de-formato.md)) y se importa con deduplicación ([10](10-deduplicacion-entre-descargas.md)). Al terminar muestra "23 movimientos nuevos, 140 ya existían".
2. **Pendientes:** lista de compras sin pago, con total y antigüedad. Reemplaza al reporte HTML actual.
3. **Movimientos:** tabla con todo el historial, buscador y filtros por fecha y moneda.

## Iteraciones siguientes
| Fase | Pantalla / función | Propuesta |
|---|---|---|
| 2 | Botones "marcar pagado" / "ignorar" en pendientes | [03](03-conciliacion-manual.md) |
| 2 | Ver qué pago cubrió cada compra | [04](04-detalle-de-matches.md) |
| 2 | Sugerencias de pagos agrupados (aceptar / rechazar) | [11](11-pagos-agrupados.md) |
| 2 | Pestaña dólares | [18](18-multi-moneda.md) |
| 3 | Categorías editables en la tabla + reglas aprendidas | [13](13-categorizacion-de-gastos.md) |
| 3 | Presupuestos por categoría | [30](30-presupuestos.md) |
| 3 | Dashboard: gasto por mes y categoría | [14](14-dashboard-con-graficos.md) |
| 3 | Cuotas vigentes | [12](12-seguimiento-de-cuotas.md) |
| 3 | Suscripciones y alertas | [15](15-deteccion-suscripciones.md), [16](16-alertas-anomalias.md) |
| 4 | Copiar pendientes para WhatsApp | [19](19-exportar-pendientes.md) |
| 4 | Notificaciones al celular | [20](20-notificaciones.md) |

## Criterios de aceptación (MVP)
- [ ] Desde el celular se puede subir el archivo de pesos y ver los pendientes.
- [ ] Subir dos veces el mismo archivo no duplica nada.
- [ ] Los pendientes coinciden con lo que da la CLI con el mismo archivo.
