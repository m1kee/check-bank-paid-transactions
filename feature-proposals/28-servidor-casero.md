# 28 · Servidor casero en el mini PC

**Categoría:** Infraestructura · **Fase:** 1 · **Esfuerzo:** M

## Objetivo
Que el mini PC (hoy con SteamOS) quede como servidor 24/7, administrado por SSH, accesible desde el Mac, el PC y el celular, **sin exponer nada a internet**.

## Sistema operativo: Debian 13 (trixie), sin escritorio
- Estable, liviano y con actualizaciones de seguridad automáticas.
- En el instalador (`netinst`), en "Selección de software" marcar **solo** `SSH server` y `standard system utilities`. Desmarcar el entorno de escritorio.
- **Alternativa:** si algún componente del mini PC no funciona (Wi-Fi, tarjeta de red), usar **Ubuntu Server LTS**, que trae un kernel más nuevo. El resto de esta guía aplica igual.

## Pasos
1. **BIOS:** activar "Restore on AC power loss → Power On" para que encienda solo después de un corte de luz. Idealmente, conectarlo por **cable de red**.
2. **Instalar Debian** (ver arriba). Crear un usuario con `sudo`.
3. **SSH con llave:** copiar tu llave (`ssh-copy-id`) desde el Mac y el PC, y luego desactivar el login con contraseña (`PasswordAuthentication no`).
4. **Tailscale:** instalarlo en el servidor, el Mac, el PC y el celular. Así se accede como `http://minipc` desde cualquier lugar, sin abrir puertos del router. Para tener HTTPS: `tailscale serve`.
5. **Firewall (`ufw`):** permitir solo tráfico de la interfaz de Tailscale (`tailscale0`) y SSH desde la red local.
6. **Actualizaciones automáticas:** `unattended-upgrades` para los parches de seguridad.
7. **Docker Engine + Compose** (repositorio oficial de Docker). La app corre como servicio con `restart: unless-stopped`.
8. **Respaldos:** ver más abajo. **No es opcional.**

## Despliegue de la app
```
/srv/bank-check/
  docker-compose.yml
  data/bank.db        ← SQLite (volumen montado)
  data/uploads/       ← archivos originales subidos
```
Para actualizar: `git pull && docker compose up -d --build` por SSH. Más adelante se puede automatizar ([26](26-contenedor-y-despliegue.md)).

## Respaldos
- Todas las noches: `sqlite3 bank.db ".backup bank-YYYYMMDD.db"` + los uploads → **restic** (cifrado) → nube (Backblaze B2, Google Drive vía rclone, etc.).
- Guardar 7 respaldos diarios, 4 semanales y 12 mensuales.
- **Probar una restauración** al menos una vez. Un respaldo que nunca se restauró no está probado.

## Criterios de aceptación
- [ ] `ssh minipc` funciona con llave, sin contraseña.
- [ ] La app responde en `http://minipc` desde el celular con datos móviles (vía Tailscale).
- [ ] El servidor vuelve solo después de desenchufarlo y enchufarlo.
- [ ] Existe un respaldo de anoche y se probó restaurarlo.
