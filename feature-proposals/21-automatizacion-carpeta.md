# 21 · Procesar automáticamente al descargar los movimientos

**Categoría:** Automatización · **Fase:** 4 · **Esfuerzo:** S–M

## Problema
Hoy el flujo es: descargar el archivo → moverlo a `pre-process-data/` → abrir la terminal → activar el venv → correr el comando. Son 5 pasos para algo que siempre es igual.

> Con la app web ([22](22-app-web.md)) esto pierde importancia: subir el archivo desde el celular ya es un solo paso. Queda como idea por si quieres cero clics desde el Mac.

## Propuesta
Vigilar `~/Downloads` (o `pre-process-data/`) y, cuando aparezca un archivo que parezca una descarga de movimientos (pesos o dólares), procesarlo solo:
- **macOS:** un `launchd` agent con `WatchPaths` (nativo, sin dependencias), o una Acción de Carpeta de Automator.
- **Multiplataforma:** la librería `watchdog`.

Para reconocer el archivo y su formato, usar el nombre del archivo o el `detect()` de [17](17-perfiles-de-formato.md).

## Criterios de aceptación
- [ ] Descargar los movimientos genera y abre el reporte sin intervención.
- [ ] Un archivo que no es de movimientos se ignora sin errores.

## Estado
✖ Descartada (10/2026): los archivos siempre se suben directamente por la web.
