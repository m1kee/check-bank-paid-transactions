# 02 · Reglas de exclusión en config, no en el código

**Categoría:** Configuración · **Fase:** 0 · **Esfuerzo:** XS

## Problema
`is_payment_description` tiene un caso especial hardcodeado:
```python
if "MERCADOPAGO" in desc and "COMERCIALSANA" in desc:
    return False
```
Cada vez que aparezca otro comercio que pasa por MercadoPago (que es una **compra**, no un pago) va a haber que editar código.

## Propuesta
Mover las excepciones a `config.py` como una lista de reglas:

```python
# Descripciones que contienen un PAYMENT_TERM pero NO son pagos
PAYMENT_EXCLUSIONS = [
    "COMERCIALSANA",
]
```

Y en `analysis.py`:
```python
if any(ex.upper() in desc for ex in config.PAYMENT_EXCLUSIONS):
    return False
```

## Extra (opcional)
Permitir expresiones regulares (`re.search`) para casos más finos, ej. `r"^MERCADOPAGO\*"` vs `r"^MERCADOPAGO PAGO"`.

## Archivos a tocar
- `config.py`, `analysis.py`, `tests/test_analysis.py` (el test existente debería seguir pasando sin cambios).

## Criterios de aceptación
- [ ] No queda ningún nombre de comercio en `analysis.py`.
- [ ] Agregar una exclusión nueva solo requiere editar `config.py`.
