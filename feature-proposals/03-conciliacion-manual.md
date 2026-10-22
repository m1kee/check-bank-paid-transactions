# 03 · Conciliación manual (marcar como pagado / ignorar)

**Categoría:** Lógica de conciliación · **Fase:** 2 · **Esfuerzo:** M

## Problema
Siempre habrá casos que el algoritmo no resuelve: un pago que cubrió dos compras, una compra que se pagó por transferencia desde otra cuenta, una compra devuelta, etc. Hoy esos casos aparecen como pendientes **en cada ejecución**, y uno tiene que acordarse de cuáles ya revisó.

## Propuesta
Un archivo `overrides.yaml` (ignorado en git porque tiene datos personales) donde se anotan decisiones manuales:

```yaml
ignore:
  - date: 2026-09-14
    description: "NETFLIX.COM"
    amount: 7990
    reason: "Lo paga mi hermano"

mark_paid:
  - date: 2026-10-02
    description: "LIDER EXPRESS"
    amount: 23450
    reason: "Pagado por transferencia 03/10"
```

El análisis carga este archivo y quita esas compras de la lista de pendientes. El reporte las muestra en una sección colapsada "Resueltas manualmente", con su motivo.

## Detalles
- Identificar una compra por `(fecha, monto, descripción normalizada)`; con eso alcanza en la práctica.
- Avisar si una regla del archivo **no encontró** ninguna compra (probablemente está mal escrita).
- Se puede usar JSON en vez de YAML para no sumar dependencias (`pyyaml`).

## Archivos a tocar
- Nuevo `overrides.py` (cargar y aplicar), `analysis.py`, `html_reporter.py`, `.gitignore`.

## Criterios de aceptación
- [ ] Una compra en `ignore` o `mark_paid` no aparece como pendiente.
- [ ] Las reglas que no coinciden con nada se advierten por consola.
