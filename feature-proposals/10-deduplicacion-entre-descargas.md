# 10 · Deduplicación entre descargas

**Categoría:** Robustez · **Fase:** 0 · **Esfuerzo:** S–M

## Problema
La vista de movimientos "al día" se descarga varias veces en el mes, y cada descarga **contiene todo lo anterior** del período más lo nuevo. Si se unen descargas ([08](08-procesamiento-por-lotes.md)) o se guardan en un historial ([09](09-historial-sqlite.md)) sin deduplicar, cada movimiento se cuenta tantas veces como descargas haya y el matching no sirve.

## Propuesta
Calcular un fingerprint por movimiento:
```python
fingerprint = sha1(f"{currency}|{date}|{description}|{amount}|{installment_details}|{n}")
```
donde `n` es el número de ocurrencia de ese mismo movimiento **dentro de la misma descarga**. Así, dos cafés idénticos el mismo día siguen siendo dos movimientos, pero el mismo café en dos descargas distintas se cuenta una sola vez.

## Riesgo a verificar
Hay que comparar dos descargas de días distintos y revisar si el banco **modifica** un movimiento ya mostrado, por ejemplo:
- una compra que primero aparece como autorización y luego con otra descripción o fecha;
- un monto que cambia (propinas, ajustes de cambio en USD).

Si pasa, el fingerprint debe usar solo campos estables, o hay que agregar una regla de "mismo movimiento, versión actualizada".

## Criterios de aceptación
- [ ] Importar la descarga del día 10 y luego la del día 20 da el mismo resultado que importar solo la del día 20.
- [ ] Dos compras legítimamente idénticas el mismo día no se pierden.
