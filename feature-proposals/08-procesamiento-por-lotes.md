# 08 · Procesar varios archivos de una vez

**Categoría:** Usabilidad · **Fase:** 2 · **Esfuerzo:** S

## Problema
Hoy hay que pasar la ruta de cada archivo. El caso típico es descargar la tabla de **pesos** y la de **dólares** ([18](18-multi-moneda.md)): hay que correr el script dos veces y salen dos reportes separados.

> En la app web ([22](22-app-web.md)) esto es simplemente permitir subir varios archivos a la vez. La lógica de unir y deduplicar va en el núcleo ([29](29-nucleo-reutilizable.md)) y la usan tanto la CLI como la web.

## Propuesta
- Hacer `input_file` opcional: si no se pasa, procesar todos los `.xls`/`.xlsx` de `pre-process-data/`.
- Aceptar varios archivos: `python main.py pesos.xls dolares.xls`.
- Un solo reporte HTML consolidado, con una sección por moneda.

## Depende de / se combina con
- [17 · Perfiles de formato](17-perfiles-de-formato.md): para saber cómo leer cada archivo.
- [10 · Deduplicación](10-deduplicacion-entre-descargas.md): si en la carpeta quedan dos descargas del mismo mes, se repiten movimientos.

## Criterios de aceptación
- [x] Sin argumentos procesa todos los archivos pendientes.
- [x] Pesos y dólares salen en el mismo reporte, cada uno con sus totales.

## Estado (v0.6.0)
La web ya aceptaba varios archivos (v0.4.0). La CLI, sin argumentos, procesa `pre-process-data/`.
