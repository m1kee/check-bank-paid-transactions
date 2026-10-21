# 09 · Historial persistente en SQLite

**Categoría:** Arquitectura · **Fase:** 1 · **Esfuerzo:** L

## Contexto
El archivo que se sube no es la cartola: es la vista de **movimientos del período en curso, al día de hoy**. Se descarga varias veces durante el mes para estar al día, y cuando el banco cierra el período, esos movimientos salen de la vista.

## Problema
Cada ejecución parte de cero y solo ve la descarga actual. Consecuencias:
- **Al cerrar el período se pierde el rastro:** una compra impaga del día 28 deja de aparecer en la vista cuando cierra la facturación, así que desaparece del reporte **sin haberse pagado**.
- Una compra hecha al final de un período y pagada al inicio del siguiente queda en vistas distintas: en una aparece como pendiente y en la otra hay un pago huérfano.
- No hay forma de preguntar "¿cuánto gasté por mes este año?" sin abrir muchos Excel.
- `data/` y `processed-archive/` se llenan de copias casi idénticas (cada descarga repite todo lo anterior del mes).

## Propuesta
Una base SQLite (`bank.db`) que vive en el **servidor casero** ([28](28-servidor-casero.md)) y que alimenta la app web ([22](22-app-web.md)). Como es el único lugar donde están los datos, no hay que sincronizar nada entre el Mac y el PC: ambos entran por el navegador. Los archivos originales también se guardan, para poder reimportar si cambia la lógica.

Tablas principales:

```sql
CREATE TABLE movements (
  id INTEGER PRIMARY KEY,
  currency TEXT NOT NULL,    -- 'CLP' | 'USD' (ver 18)
  date TEXT NOT NULL,
  card_type TEXT,
  description TEXT,
  city TEXT,
  installments TEXT,
  installment_details TEXT,
  amount NUMERIC NOT NULL,
  fingerprint TEXT UNIQUE,   -- evita duplicados entre descargas (ver 10)
  first_seen_at TEXT,        -- primera descarga donde apareció
  last_seen_at TEXT          -- última descarga donde apareció
);

CREATE TABLE matches (
  purchase_id INTEGER REFERENCES movements(id),
  payment_id INTEGER REFERENCES movements(id),
  method TEXT                -- 'auto' | 'manual'
);
```

Flujo nuevo: **importar** descarga → se insertan solo los movimientos nuevos → **analizar** sobre todo el historial (o un rango).

Una compra pendiente sigue pendiente aunque ya no aparezca en la vista del banco, hasta que se empareje con un pago o la marques a mano ([03](03-conciliacion-manual.md)).

## Lo que habilita
- [10 · Deduplicación](10-deduplicacion-entre-descargas.md) casi gratis (`fingerprint UNIQUE`).
- [03 · Conciliación manual](03-conciliacion-manual.md) guardada en la tabla `matches`.
- [14 · Dashboard](14-dashboard-con-graficos.md), [15 · Suscripciones](15-deteccion-suscripciones.md) y comparaciones entre meses.
- Con `last_seen_at` se puede detectar un movimiento que **desapareció** de la vista sin que cerrara el período (ej. una compra anulada o reversada).

## Riesgos
- Cambio grande de arquitectura: conviene hacerlo **después** de tener el núcleo separado ([29](29-nucleo-reutilizable.md)) y con tests ([23](23-tests-y-ci.md)).
- Si el servidor muere sin respaldo, se pierde el historial y las categorías: los respaldos de [28](28-servidor-casero.md) son obligatorios.
- La DB tiene datos sensibles: va al `.gitignore` (ver [25](25-privacidad-retencion-cifrado.md)).

## Criterios de aceptación
- [ ] Importar dos descargas del mismo mes no duplica movimientos.
- [ ] Una compra impaga sigue apareciendo como pendiente después del cierre del período.
- [ ] Un pago del período siguiente puede emparejar una compra del período anterior.
