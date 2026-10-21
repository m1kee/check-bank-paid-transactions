# 05 · Escapar el contenido del reporte HTML

**Categoría:** Seguridad / Bug · **Fase:** 0 · **Esfuerzo:** XS

## Problema
`html_reporter.py` mete `Description` y `City` directo en el HTML con f-strings. Las descripciones vienen del banco y las escribe el **comercio**. Una descripción con `<`, `&` o comillas rompe el layout, y en el peor caso un texto como `<script>` se ejecutaría al abrir el reporte.

## Propuesta
```python
from html import escape

desc = escape(str(row.get('Description', '')))
city = escape(str(row.get('City', '')))
```
Lo mismo para `start_date` y cualquier otro valor externo que llegue al template.

## Nota
En la app web ([22](22-app-web.md)) esto lo resuelve Jinja2, que escapa todo por defecto. Igual vale la pena arreglarlo ya, porque son 5 minutos y el reporte HTML se sigue usando hasta que exista la web.

## Extra
- El reporte carga la fuente Inter desde Google Fonts, así que cada vez que se abre un reporte con datos bancarios se hace una petición externa. Se podría usar la fuente del sistema (`system-ui`) y que el reporte funcione 100% offline.

## Criterios de aceptación
- [ ] Una descripción `"<b>X</b> & Y"` se ve literal en el reporte.
- [ ] Test unitario que lo verifique.
