# 17 · Perfiles de formato (pesos, dólares y otros bancos)

**Categoría:** Arquitectura · **Fase:** 0 · **Esfuerzo:** M–L

## Problema
Todo el preprocesamiento asume un único formato: `.xls`, 18 filas de encabezado y columnas fijas en `config.py`. Pero ya hay al menos **dos formatos**: la tabla de pesos y la de dólares ([18](18-multi-moneda.md)), que se descargan por separado. Si algún día cambias de banco o usas tarjetas de más de uno, pasa lo mismo.

## Propuesta
Perfiles de formato:
```
parsers/
  base.py        # interfaz: detect(path) -> bool, parse(path) -> DataFrame normalizado
  bank_clp.py    # la vista de movimientos en pesos (el formato de hoy)
  bank_usd.py    # la vista de movimientos en dólares
```
- Cada parser devuelve el **mismo esquema** normalizado (`Currency`, `Date`, `Description`, `Amount`, `Installments`...).
- `detect()` reconoce el formato automáticamente (por encabezados, ver [07](07-deteccion-automatica-encabezado.md)); también se puede forzar con `--format`.
- Más adelante, otro banco es solo un archivo nuevo en `parsers/`.

## Criterios de aceptación
- [ ] El formato actual funciona como un parser más, sin cambios de comportamiento.
- [ ] Agregar un formato nuevo no requiere tocar `analysis.py`.
