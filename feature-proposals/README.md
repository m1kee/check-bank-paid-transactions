# 💡 Feature Proposals

Ideas de mejoras y features nuevos para **check-bank-paid-transactions**. Cada archivo explica el problema, la propuesta, qué archivos tocar y cómo saber que quedó listo.

> **Sobre los datos de entrada:** el script no usa la cartola (que siempre llega a mes vencido), sino la **vista de movimientos del período en curso, al día de hoy**. Se descarga varias veces al mes, y cada descarga repite lo anterior. Los movimientos en **pesos y en dólares** son dos tablas distintas que se descargan por separado y pueden tener formatos diferentes.

## Hacia dónde va

```
Mac / PC / celular ──(Tailscale)──► mini PC con Debian 13
                                     ├─ App web (FastAPI + HTMX)
                                     ├─ SQLite: historial, categorías, presupuestos
                                     └─ Respaldo diario cifrado → nube
```

La lógica (leer archivos, deduplicar, matching, categorías) vive en un **núcleo** que usan tanto la CLI como la web. Por eso la Fase 0 no necesita UI y se puede hacer ya, en paralelo con montar el servidor.

**Esfuerzo:** XS (< 1 h) · S (unas horas) · M (1–2 días) · L (varios días)

## Fase 0 · Base sin UI ✅ (v0.2.0)
Lógica que después solo hay que mostrar en la web. Se prueba con la CLI.

| # | Feature | Esfuerzo | Estado |
|---|---|---|---|
| 02 | [Exclusiones configurables](02-exclusiones-configurables.md) | XS | ✅ v0.2.0 |
| 05 | [Escapar el contenido del reporte HTML](05-escapar-html.md) | XS | ✅ v0.2.0 |
| 27 | [Fechas reales en el Excel limpio](27-fechas-reales-en-excel-limpio.md) | XS | ✅ v0.2.0 |
| 29 | [Separar el núcleo de la CLI](29-nucleo-reutilizable.md) | M | ✅ v0.2.0 |
| 23 | [Más tests y CI](23-tests-y-ci.md) | M | ✅ v0.2.0 |
| 07 | [Detectar el encabezado automáticamente](07-deteccion-automatica-encabezado.md) | S | ✅ v0.2.0 |
| 17 | [Perfiles de formato (pesos, dólares)](17-perfiles-de-formato.md) | M–L | ✅ v0.7.0 (formato USD validado con un archivo real) |
| 10 | [Deduplicación entre descargas](10-deduplicacion-entre-descargas.md) | S–M | ✅ v0.2.0 (el historial la usa desde v0.3.0) |
| 01 | [Matching que respeta fechas](01-matching-con-fechas.md) | M | ✅ v0.2.0 |

## Fase 1 · Servidor + app web MVP ⭐
Subir archivos, ver pendientes y ver el historial desde cualquier dispositivo.

| # | Feature | Esfuerzo |
|---|---|---|
| 28 | [Servidor casero en el mini PC](28-servidor-casero.md) | M |
| 26 | [Contenedor, dependencias y despliegue](26-contenedor-y-despliegue.md) | S — 🟡 contenedor en v0.5.0; falta el despliegue en un comando (Fase 4) |
| 09 | [Historial en SQLite](09-historial-sqlite.md) | L — ✅ v0.3.0 (CLI con `--db`; las decisiones manuales van en `resolutions` desde v0.6.0) |
| 22 | [App web (MVP)](22-app-web.md) | L — ✅ v0.4.0 (falta probarla en el celular vía Tailscale) |
| 24 | [Logging e idioma consistente](24-logging-e-idioma.md) | S — ✅ v0.5.0 |

## Fase 2 · Conciliación completa en la UI

| # | Feature | Esfuerzo |
|---|---|---|
| 03 | [Marcar pagado / ignorar](03-conciliacion-manual.md) | M — ✅ v0.6.0 |
| 04 | [Ver qué pago cubrió cada compra](04-detalle-de-matches.md) | S — ✅ v0.6.0 |
| 18 | [Movimientos en dólares](18-multi-moneda.md) | M — ✅ v0.7.0 |
| 08 | [Subir varios archivos a la vez](08-procesamiento-por-lotes.md) | S — ✅ v0.6.0 |
| 11 | [Pagos que cubren varias compras](11-pagos-agrupados.md) | M — ✅ v0.6.0 |

## Fase 3 · Entender los gastos

| # | Feature | Esfuerzo |
|---|---|---|
| 13 | [Catalogar gastos (categorías y reglas)](13-categorizacion-de-gastos.md) | M — ✅ v0.6.0 |
| 30 | [Presupuestos por categoría](30-presupuestos.md) | S–M — ✅ v0.6.0, alertas en v0.7.0 |
| 14 | [Dashboard con gráficos](14-dashboard-con-graficos.md) | M — ✅ v0.6.0 |
| 12 | [Seguimiento de cuotas](12-seguimiento-de-cuotas.md) | M — ✅ v0.6.0 |
| 15 | [Detectar suscripciones](15-deteccion-suscripciones.md) | M — ✅ v0.6.0 |
| 16 | [Alertas de duplicados y anomalías](16-alertas-anomalias.md) | S — ✅ v0.6.0 |

## Fase 4 · Comodidad y operación

| # | Feature | Esfuerzo |
|---|---|---|
| 19 | [Copiar / exportar pendientes](19-exportar-pendientes.md) | XS — ✅ v0.6.0 |
| 20 | [Notificaciones](20-notificaciones.md) | M — ✅ v0.7.0 (ntfy) |
| 25 | [Privacidad: retención y respaldos cifrados](25-privacidad-retencion-cifrado.md) | S–M — ⏸ pospuesta: al principio, respaldo en el mismo servidor (ver 28); más adelante, el NAS |
| 06 | [Flags de la CLI](06-flags-cli.md) | S — ✅ v0.6.0 |
| 21 | [Procesar al descargar (sin abrir la web)](21-automatizacion-carpeta.md) | S–M — ✖ descartada: los archivos siempre se suben por la web |

## Dependencias clave

- **29 (núcleo)** va primero: sin él, la web duplicaría la lógica de la CLI.
- **28 (servidor)** no depende de nada del código: se puede montar en paralelo con la Fase 0.
- **09 (SQLite)** evita que una compra impaga desaparezca al cerrar el período. Necesita **10** porque cada descarga repite lo anterior.
- **17 (perfiles)** es la base de **18** (dólares).
- **01 (matching por fechas)** es la base de **04** y **11**.
- **13 (categorías)** es la base de **30**, **14** y **15**.

## Plantilla para nuevas propuestas

```markdown
# NN · Título

**Categoría:** … · **Fase:** ? · **Esfuerzo:** ?

## Problema
## Propuesta
## Archivos a tocar
## Riesgos
## Criterios de aceptación
- [ ] …
```
