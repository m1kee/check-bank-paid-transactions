# 15 · Detectar suscripciones y cobros recurrentes

**Categoría:** Nuevo análisis · **Fase:** 3 · **Esfuerzo:** M

## Problema
Las suscripciones (streaming, apps, gimnasio, iCloud) se cobran solas, son fáciles de olvidar y suben de precio sin aviso.

## Propuesta
Con el historial ([09](09-historial-sqlite.md)), detectar comercios que:
- Aparecen en **3 o más meses** distintos,
- con un intervalo de ~30 días (±5),
- y un monto parecido (±15%).

Mostrar una tabla "Suscripciones detectadas" con monto actual, costo anual estimado y una alerta si **el precio subió** respecto del cobro anterior.

## Criterios de aceptación
- [ ] Un cobro mensual de Netflix durante 3 meses aparece detectado.
- [ ] Una subida de precio se marca en el reporte.
