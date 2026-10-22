# 20 · Notificaciones (Telegram / email)

**Categoría:** Automatización · **Fase:** 4 · **Esfuerzo:** M

## Problema
La herramienta solo sirve si te acuerdas de correrla.

## Propuesta
Al terminar el análisis, enviar un resumen corto:
> 🧾 3 compras sin pagar · $27.950 · la más antigua tiene 12 días

Opciones, de más simple a más compleja:
1. **Notificación local de macOS** (`osascript -e 'display notification ...'`), sin dependencias.
2. **Bot de Telegram**: un `requests.post` al API; token en `.env` (ya ignorado en git).
3. **Email** por SMTP.

Combinado con [21](21-automatizacion-carpeta.md), el flujo queda: descargas los movimientos → te llega el resumen al celular.

## Privacidad
Enviar solo el resumen (cantidad y total), no el detalle de comercios, salvo que lo actives explícitamente.

## Criterios de aceptación
- [x] Configurable y apagado por defecto.
- [x] Ninguna credencial queda en el repo.

## Estado
v0.7.0 con [ntfy](https://ntfy.sh) (gratis, sin cuenta). Se envía después de cada subida por la web, no desde la CLI. Avisos únicos (presupuestos, duplicados, montos inusuales) registrados en la tabla `notifications`; si un envío falla, se reintenta en la siguiente subida.
