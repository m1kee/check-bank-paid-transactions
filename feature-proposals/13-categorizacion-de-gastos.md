# 13 · Categorizar gastos automáticamente

**Categoría:** Nuevo análisis · **Fase:** 3 · **Esfuerzo:** M

## Problema
Las descripciones del banco (`UBER *TRIP`, `LIDER EXPRESS 123`, `SPOTIFY P1A2B3`) no dicen en qué se va la plata.

## Propuesta
Reglas simples en un archivo de configuración:
```python
CATEGORY_RULES = {
    "Supermercado": ["LIDER", "JUMBO", "UNIMARC", "SANTA ISABEL"],
    "Transporte":   ["UBER", "DIDI", "CABIFY", "COPEC", "SHELL"],
    "Suscripciones":["NETFLIX", "SPOTIFY", "YOUTUBE", "APPLE.COM"],
    "Delivery":     ["RAPPI", "PEDIDOSYA", "UBER EATS"],
}
```
- La primera regla que coincide gana; lo que no coincide queda en "Otros".
- El reporte muestra el total por categoría y la lista de "Otros" más frecuentes, para ir agregando reglas.

## En la app web ([22](22-app-web.md))
- La categoría se cambia directo en la tabla de movimientos (un select por fila).
- Al cambiarla, la app ofrece: *"¿Siempre que diga UBER EATS → Delivery?"*, y con un clic se crea la regla. Así las reglas se van armando con el uso, sin editar archivos.
- Una vista de **"Sin categoría"**, ordenada por monto o frecuencia, para ir limpiándola de a poco.
- Las reglas y categorías viven en SQLite ([09](09-historial-sqlite.md)), no en `config.py`.
- Categorías personalizables (crear, renombrar, unir), con un color y un ícono para el dashboard.

## Evolución posible
- Usar un LLM (ej. Claude) para **sugerir** reglas a partir de las descripciones de "Otros", y que tú las apruebes. Ojo: eso implica enviar descripciones de compras a un servicio externo.

## Criterios de aceptación
- [ ] Cada movimiento tiene una categoría.
- [ ] El reporte muestra totales por categoría.
