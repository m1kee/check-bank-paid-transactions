# 26 · Contenedor, dependencias y despliegue

**Categoría:** Calidad / Infraestructura · **Fase:** 1 (contenedor) y 4 (automatización) · **Esfuerzo:** S

## Problema
- `requirements.txt` fija versiones de 2024 (pandas 2.2.2, numpy 1.26.4), anteriores a Python 3.13 (el de tu venv). Instalar en un equipo nuevo puede requerir compilar numpy.
- Las rutas (`data`, `reports`, ...) son relativas al directorio actual.
- El README habla de una carpeta `account_analyzer/` que no existe y no menciona el reporte HTML ni `--start-date`.

## Propuesta
**Fase 1 (junto con [28](28-servidor-casero.md)):**
- `pyproject.toml` con dependencias actualizadas.
- `Dockerfile` + `docker-compose.yml`: imagen de Python, la app web y un volumen para `data/`.
- Rutas tomadas de una variable de entorno (`BANK_CHECK_DATA_DIR`), no del directorio actual.
- README actualizado: cómo correr la CLI en local y cómo desplegar en el servidor.

**Fase 4:**
- Desplegar con un comando desde el Mac (`make deploy` → `ssh minipc 'cd /srv/bank-check && git pull && docker compose up -d --build'`).
- Opcional: GitHub Actions que corra los tests ([23](23-tests-y-ci.md)) y despliegue vía Tailscale si pasan.

## Criterios de aceptación
- [x] `docker compose up` levanta la app en un equipo limpio. *(probado en local con Docker Desktop)*
- [ ] Desplegar una versión nueva es un solo comando. *(Fase 4, cuando exista el servidor)*

## Estado (v0.5.0)
- `pyproject.toml` + uv (v0.2.0), `Dockerfile`, `docker-compose.yml` y `.dockerignore` (v0.5.0).
- Rutas con `BANKCHECK_DATA_DIR` (en el contenedor, `/data`).
- El puerto se publica solo en `127.0.0.1` por defecto; en el servidor se expone con `tailscale serve` o con `BANKCHECK_BIND`.
- El CI construye la imagen en cada push.
