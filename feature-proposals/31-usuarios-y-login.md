# 31 · Usuarios y login con Google / Microsoft

**Categoría:** Seguridad · **Fase:** 5 · **Esfuerzo:** L (login M + datos por usuario L)

## Problema
La app web ([22](22-app-web.md)) tiene una sola contraseña (HTTP Basic, `BANKCHECK_PASSWORD`), sin cerrar sesión, sin límite de intentos y sin saber **quién** entró. Por eso hoy solo puede estar detrás de un proxy que pide identificarse: no se puede abrir a otras personas ni exponer a internet.

Además, la base no tiene noción de usuario: las 8 tablas del historial ([09](09-historial-sqlite.md)) son de un solo dueño. Agregar un login sin separar los datos dejaría a todos viendo los movimientos de todos.

## Propuesta

### 1. Identidad: OpenID Connect (Google y Microsoft)
- "Continuar con Google" y "Continuar con Microsoft" con [Authlib](https://docs.authlib.org/) (cliente OIDC para Starlette/FastAPI). Microsoft cubre las cuentas personales (Outlook/Hotmail) y las de trabajo.
- Apple queda fuera por ahora: exige la cuenta de desarrollador pagada.
- **El usuario se identifica por `iss` + `sub`** del proveedor, no por el correo (el correo puede cambiar). Solo se aceptan correos con `email_verified`.
- **Solo por invitación:** un login de Google demuestra quién eres, no que tengas permiso. Un correo que no está invitado ve "No tienes acceso" y no se crea nada.
- **Superadmin:** el correo de `BANKCHECK_ADMIN_EMAIL` lo es al primer ingreso. `BANKCHECK_PASSWORD` queda como **acceso de emergencia** del superadmin (por si se cae el proveedor o vence un secreto), con límite de intentos.

### 2. Sesiones
- Tabla `sessions` en la base (en ella solo el sha256 del token). Cookie `__Host-session`: `HttpOnly`, `Secure`, `SameSite=Lax`, sin `Domain`. 30 días sin uso, y "Cerrar sesión" la borra.
- **CSRF:** un token en cada formulario y en `hx-headers` para HTMX, comparado con el de la sesión, más la revisión del `Origin`.
- `state`, `nonce` y PKCE en el flujo OIDC (Authlib los maneja).

### 3. Datos por hogar
- Tabla `households` (un conjunto de datos: "Casa", "Pyme"…) y `memberships` (usuario, hogar, rol `owner` o `viewer`).
- Columna `household_id` en `imports`, `movements`, `resolutions`, `dismissed_suggestions`, `categories` (con sus presupuestos), `category_rules`, `notifications` y `dismissed_alerts`. Lo único (`UNIQUE`) pasa a ser único por hogar.
- **Migración v4:** crea un hogar con todo lo que ya existe y deja al superadmin como `owner`. No se pierde nada.
- **Toda consulta pasa por el hogar de la sesión**, en un solo lugar (una dependencia de FastAPI que entrega `user` y `household`), nunca armada a mano en cada ruta.
- Las notificaciones ([20](20-notificaciones.md)) pasan a configurarse por hogar en la app, no por variables de entorno.
- **CLI:** sigue trabajando sobre un hogar (`--household`, por defecto el primero).

### 4. Administración
- Página "Usuarios" (superadmin): invitar por correo, cambiar el rol, desactivar (corta sus sesiones al tiro).
- Página "Mi cuenta": hogares a los que pertenece, sesiones abiertas, cerrar las demás.

## Qué hay que configurar fuera de la app
- **Google:** un proyecto en Google Cloud con su pantalla de consentimiento (tipo External; los scopes `openid email profile` no necesitan la revisión de Google) y un cliente OAuth "Aplicación web" con el redirect `https://<host>/auth/google/callback` (y `http://127.0.0.1:8000/...` para desarrollo). Publicar la app ("In production"): en modo prueba, Google corta la sesión cada 7 días.
- **Microsoft:** un registro de aplicación en Microsoft Entra para "cuentas de cualquier organización y cuentas personales", con su redirect. **Su secreto vence (máximo 24 meses):** anotar la fecha y avisar antes.
- Los client ID y secretos van como variables de entorno (`BANKCHECK_GOOGLE_CLIENT_ID`, `…_SECRET`, `BANKCHECK_MICROSOFT_…`) y, en el servidor, como secretos cifrados.

## Archivos a tocar
- `bankcheck/history.py`: migración v4 (hogares, usuarios, membresías, sesiones, `household_id`).
- `bankcheck/web/auth.py` (nuevo): rutas `/login`, `/auth/<proveedor>/callback`, `/logout`, sesiones, CSRF y la dependencia `current_user`.
- `bankcheck/web/app.py`: reemplazar `require_password` por la dependencia nueva y pasar el hogar a cada consulta.
- `bankcheck/web/templates/`: login, usuarios, mi cuenta; botón de cerrar sesión.
- `bankcheck/cli.py`: `--household`.
- `pyproject.toml`: `authlib` (y `httpx`, que usa su cliente).
- `tests/`: login simulado (sin llamar a Google), aislamiento entre hogares, CSRF, invitaciones, migración v4 sobre una base v3.
- `readme.md`, `docker-compose.yml`: las variables nuevas.

## Riesgos
- **Fuga entre hogares:** el error más grave posible. Mitigación: un solo punto que filtra por hogar y un test por ruta con dos hogares ("el usuario B no ve nada de A").
- **Quedar fuera:** si se cae el proveedor o vence el secreto de Microsoft. Mitigación: el acceso de emergencia del superadmin.
- **Migración:** tocar todas las tablas. Mitigación: respaldo antes, migración probada sobre una copia de la base real y un camino para volver a la versión anterior.
- **Cambio incompatible:** la configuración y el acceso cambian (0.x → sube la minor, con nota en el CHANGELOG).

## Criterios de aceptación
- [ ] Se entra con Google y con Microsoft; un correo no invitado no entra y no deja rastro.
- [ ] El superadmin invita, cambia roles y desactiva usuarios; desactivar corta sus sesiones.
- [ ] Dos hogares no ven nada uno del otro (test por cada ruta).
- [ ] Los formularios rechazan peticiones sin token CSRF o de otro origen.
- [ ] La migración conserva todos los datos existentes en el primer hogar.
- [ ] `BANKCHECK_PASSWORD` sirve como acceso de emergencia del superadmin, con límite de intentos.
- [ ] La CLI sigue funcionando sobre un hogar.
