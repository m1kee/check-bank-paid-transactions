# 29 · Separar el núcleo de la CLI

**Categoría:** Arquitectura · **Fase:** 0 · **Esfuerzo:** M

## Problema
Hoy la lógica está mezclada con la consola y los archivos: `analyze_movements` lee el Excel, filtra, hace el matching, imprime con `print` y genera el HTML, todo en una función. La app web ([22](22-app-web.md)) necesita **la misma lógica** pero sin `print`, sin leer desde una ruta y sin abrir el navegador.

## Propuesta
Un paquete con funciones puras que reciben y devuelven datos:

```
bankcheck/
  parsers/        # leer archivo de pesos / dólares → DataFrame normalizado (17)
  dedup.py        # fingerprint de movimientos (10)
  matching.py     # compras vs pagos → matched, unpaid, orphans (01, 04, 11)
  categorize.py   # reglas de categorías (13)
  models.py       # dataclasses de resultado
cli.py            # la CLI actual, usando bankcheck
web/              # la app web, usando bankcheck
```

- Ninguna función del núcleo hace `print`, lee rutas fijas ni abre el navegador.
- La CLI sigue funcionando igual que hoy y sirve para probar cambios rápido, sin servidor.

## Por qué primero
- Es la condición para que la web no sea una copia de la lógica.
- Hace posibles los tests de [23](23-tests-y-ci.md).

## Criterios de aceptación
- [ ] `python cli.py archivo.xls` da el mismo resultado que hoy.
- [ ] El matching se puede llamar desde un test con un DataFrame armado a mano.
