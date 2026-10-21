# 19 · Exportar o copiar los pendientes

**Categoría:** Usabilidad · **Fase:** 4 · **Esfuerzo:** XS

## Problema
Una vez que sabes qué falta pagar, lo más probable es que quieras **hacer algo** con eso: pagarlo, mandárselo a alguien o anotarlo. Hoy hay que copiar a mano desde la tabla HTML.

## Propuesta
En el reporte HTML:
- Botón **"Copiar lista"** que copia al portapapeles un texto listo para pegar en WhatsApp:
  ```
  Pendientes al 21/10/2026:
  • 03/10 UBER TRIP — $4.500
  • 07/10 LIDER EXPRESS — $23.450
  Total: $27.950
  ```
- Botón **"Descargar CSV"**.

En la CLI: `--export pendientes.csv`.

## Criterios de aceptación
- [ ] El texto copiado tiene formato de pesos chilenos y el total.
