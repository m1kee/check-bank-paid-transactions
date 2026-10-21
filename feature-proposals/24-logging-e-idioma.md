# 24 · Logging y un solo idioma en mensajes y código

**Categoría:** Calidad · **Fase:** 1 · **Esfuerzo:** S

## Problema
- Los mensajes mezclan idiomas: `"[Analyzing]: Reading clean file"` y luego `"Filtro de fecha activo"`; `"Generando reporte visual HTML..."` junto a `"--- Analysis Complete ---"`. Lo mismo en comentarios y en el `--help`.
- Todo es `print`, así que no se puede bajar el detalle (`--quiet`) ni subirlo (`--verbose`) para depurar.
- Los errores en `analysis.py` hacen `return` en vez de terminar con código de salida ≠ 0, así que un script que lo llame no sabe que falló.

## Propuesta
- Elegir un idioma para lo que ve el usuario (sugerencia: **español**, ya que el reporte HTML está en español) y otro para el código (inglés, como está hoy).
- Usar el módulo `logging` con niveles; flags `-v/--verbose` y `-q/--quiet`.
- Que los errores se propaguen como excepciones y `main.py` decida el código de salida.

## Criterios de aceptación
- [ ] Todos los mensajes de consola están en un solo idioma.
- [ ] Un error de lectura termina con exit code 1.
