# 25 · Privacidad: retención y limpieza de archivos

**Categoría:** Seguridad · **Fase:** 4 · **Esfuerzo:** S–M

## Problema
Cada ejecución deja **tres copias** de los movimientos bancarios en disco: el archivo original (`processed-archive/`), el Excel limpio (`data/`) y el reporte (`reports/`). Se acumulan sin límite, en texto plano, y probablemente dentro de carpetas que se respaldan en iCloud/Dropbox.

> Con el servidor ([28](28-servidor-casero.md)), el historial vive en SQLite y los archivos sueltos en `data/` y `reports/` dejan de ser necesarios. Lo importante pasa a ser que **los respaldos vayan cifrados** (restic ya lo hace) y que la app solo sea accesible vía Tailscale.

## Propuesta
1. **Retención configurable:** `RETENTION_DAYS = 90`; un comando `python main.py --cleanup` borra lo más antiguo.
2. **Menos copias:** con [09](09-historial-sqlite.md), `data/` deja de ser necesario.
3. **Opcional:** cifrar `processed-archive/` y la DB (ej. `cryptography` con la clave en el Keychain de macOS vía `keyring`).
4. Comprobar que `.gitignore` cubre todo lo sensible (hoy está bien: `data/`, `processed-archive/`, `reports/`, `pre-process-data/`).

## Criterios de aceptación
- [ ] `--cleanup` borra los archivos más antiguos que la retención configurada y lista lo que borró.

## Estado
⏸ Pospuesta (10/2026). Al principio, un respaldo en el mismo servidor como parte de [28](28-servidor-casero.md); más adelante se puede usar el NAS.
