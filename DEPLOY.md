# Guía de despliegue — Nutrientrena

Documento de entrega para operar Nutrientrena en producción (Railway).

---

## Acceso en producción

| Recurso | URL |
|---------|-----|
| Aplicación web | https://nutrientrena-production.up.railway.app/app/login.html |
| API Swagger | https://nutrientrena-production.up.railway.app/api/docs |
| Health check | https://nutrientrena-production.up.railway.app/api/health |

### Credenciales iniciales de administrador

```
Email:    vallejoj203k@gmail.com
Password: Admin123!
```

> **Cambiar la contraseña en el primer acceso** usando el menú de perfil o vía `PUT /api/users/{id}/update`.

---

## Variables de entorno en Railway

Ir a **Railway → Proyecto → Variables** y configurar:

### Obligatorias

| Variable | Descripción |
|----------|-------------|
| `SECRET_KEY` | Clave secreta para firmar JWT. Generar con: `openssl rand -hex 32` |
| `FRONTEND_URL` | URL pública de la app (ej. `https://nutrientrena-production.up.railway.app`) |
| `ALLOWED_ORIGINS` | Mismo valor que `FRONTEND_URL`. Si se omite, usa `FRONTEND_URL` automáticamente |
| `RESEND_API_KEY` | API key de [resend.com](https://resend.com). Formato: `re_xxxxxxxxxxxx` |
| `MAIL_FROM` | Email verificado en Resend (ej. `noreply@tudominio.com`) |

> `DATABASE_URL` / `MYSQL_URL` la genera Railway automáticamente al conectar el plugin MySQL.

### Cloudflare R2 (almacenamiento de imágenes)

| Variable | Descripción |
|----------|-------------|
| `AWS_ACCESS_KEY_ID` | Access key del token R2 (en Cloudflare → R2 → Manage API Tokens) |
| `AWS_SECRET_ACCESS_KEY` | Secret key del mismo token |
| `AWS_BUCKET` | Nombre del bucket (ej. `nutrientrena-files`) |
| `AWS_ENDPOINT_URL` | `https://<account-id>.r2.cloudflarestorage.com` |
| `R2_PUBLIC_URL` | `https://pub-<id>.r2.dev` (activar acceso público en el bucket) |
| `AWS_DEFAULT_REGION` | `auto` |

### Opcionales (ya tienen valor por defecto)

| Variable | Defecto | Descripción |
|----------|---------|-------------|
| `ALGORITHM` | `HS256` | Algoritmo de firma JWT |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` | Expiración del token (24 h) |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `30` | Expiración del refresh token |
| `DEBUG` | `false` | Mostrar stack traces en respuestas de error 500 |

---

## Primer despliegue — Checklist

### 1. Configurar variables de entorno
- [ ] Todas las variables obligatorias ingresadas en Railway
- [ ] `SECRET_KEY` generada con `openssl rand -hex 32` (no usar el valor del `.env.example`)
- [ ] `FRONTEND_URL` y `ALLOWED_ORIGINS` apuntan a la URL de Railway

### 2. Ejecutar migraciones

Railway ejecuta automáticamente el comando de inicio. Verificar que el `Procfile` o el comando de Railway incluye:

```bash
alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Si las migraciones no corren automáticamente, ejecutar desde Railway Shell:

```bash
alembic upgrade head
```

Verificar que se aplicaron las **10 migraciones**:

```bash
alembic history --verbose
```

### 3. Ejecutar seeds

Los seeds son idempotentes (se pueden ejecutar varias veces sin duplicar datos):

```bash
python -m app.seeds.run_seeds
```

Esto crea:
- Parámetros del sistema (estados de cliente, géneros, niveles de actividad, objetivos)
- Roles base (superadmin, admin, setter, closer, coach, client)
- Menús del sidebar
- Usuario administrador inicial (credenciales arriba)
- Plantilla de formulario de intake por defecto

### 4. Verificar health

```bash
curl https://nutrientrena-production.up.railway.app/api/health
# Esperado: {"status":"ok","app":"NutrientrenaAPI"}
```

### 5. Verificar Swagger

Abrir https://nutrientrena-production.up.railway.app/api/docs → deben aparecer 30 secciones con todos los endpoints documentados.

### 6. Verificar login

```bash
curl -X POST https://nutrientrena-production.up.railway.app/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"vallejoj203k@gmail.com","password":"Admin123!"}'
```

Respuesta esperada: `{"success":true,"data":{"token":"eyJ...","refresh_token":"eyJ..."}}`

---

## Despliegues posteriores (actualizaciones)

Railway despliega automáticamente en cada push a `main`. El pipeline de CI corre antes:

1. **Lint** con ruff — falla si hay errores de sintaxis
2. **Validación de modelos** — verifica que los imports de SQLAlchemy son correctos
3. **Validación de rutas** — verifica que FastAPI carga todos los routers
4. **Validación de migraciones** — verifica que existen archivos en `alembic/versions/`
5. **Suite pytest** — 47 tests, cobertura ≥ 40%

Si algún job falla, Railway **no despliega**.

### Agregar una migración nueva

```bash
alembic revision --autogenerate -m "descripcion_del_cambio"
# Revisar el archivo generado en alembic/versions/
# Ajustar si es necesario (autogenerate no detecta todo)
alembic upgrade head   # aplicar localmente
git add alembic/versions/
git commit -m "feat: migration descripcion_del_cambio"
git push
```

Railway aplicará la migración al reiniciar el servicio con `alembic upgrade head`.

---

## Estructura de roles y permisos

| ID | Slug | Nombre | Acceso |
|----|------|--------|--------|
| 1 | `superadmin` | Superadmin | Todo, incluyendo roles y menús |
| 2 | `admin` | Administrador | Gestión de usuarios, clientes y configuración |
| 3 | `setter` | Setter | Crear y gestionar clientes |
| 4 | `closer` | Closer | Ver y actualizar estado de clientes |
| 5 | `coach` | Coach | Solo sus propios clientes |
| 6 | `client` | Cliente | Sin acceso al panel (solo formularios públicos) |

---

## Almacenamiento R2 — Carpetas del bucket

| Carpeta | Uso |
|---------|-----|
| `profiles/` | Fotos de perfil de usuarios |
| `checkins/` | Fotos de check-ins semanales |
| `progress/` | Fotos de progreso (hasta 3 por registro) |
| `aliments/` | Imágenes de alimentos |
| `uploads/` | Archivos generales |

Límite por archivo: **10 MB** · Formatos aceptados: JPG, PNG, WEBP, GIF

---

## Seguridad — Configuración activa en producción

- **CORS**: solo el origen de `ALLOWED_ORIGINS` o `FRONTEND_URL`. Nunca wildcard `*` en producción.
- **Rate limiting**: 10 req/min en login, 5 req/min en recuperar contraseña (IP-based).
- **Security headers** en todas las respuestas:
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `X-XSS-Protection: 1; mode=block`
  - `Referrer-Policy: strict-origin-when-cross-origin`
  - `Permissions-Policy: camera=(), microphone=(), geolocation=()`
- **Stack traces**: ocultos en producción (`DEBUG=false`). Activar solo para debugging puntual.

---

## Emails transaccionales (Resend)

La plataforma envía los siguientes emails automáticos:

| Evento | Destinatario |
|--------|-------------|
| Recuperación de contraseña | Usuario que la solicita |
| Entrega de plan (dieta + rutina) | Cliente |
| Asignación de formulario de intake | Cliente (incluye link público) |
| Check-in recibido | Coach del cliente |
| Notas del coach añadidas | Cliente |

Para probar el envío de email desde producción:

```bash
POST /api/plans/test-email
Authorization: Bearer <token>
{ "to": "test@ejemplo.com" }
```

---

## Monitoreo

| Indicador | Cómo verificar |
|-----------|----------------|
| API activa | `GET /api/health` → `{"status":"ok"}` |
| Migraciones aplicadas | `alembic current` desde Railway Shell |
| Últimos errores | Logs de Railway → filtrar por `ERROR` o `500` |
| Cobertura de tests | Artefacto `.coverage` en cada run de GitHub Actions |

---

## Instalación local para desarrollo

```bash
git clone https://github.com/vallejoj203k/nutrientrena.git
cd nutrientrena

python -m venv venv
source venv/bin/activate        # Mac/Linux
venv\Scripts\activate           # Windows

pip install -r requirements.txt
pip install -r requirements-dev.txt   # incluye pytest y herramientas de dev

cp .env.example .env
# Editar .env con credenciales locales

alembic upgrade head
python -m app.seeds.run_seeds

uvicorn app.main:app --reload
# Servidor en http://localhost:8000
# Swagger en http://localhost:8000/api/docs
```

### Correr los tests localmente

```bash
DATABASE_URL="sqlite:///./test_nutrientrena.db" \
SECRET_KEY="test-secret" \
AWS_ACCESS_KEY_ID="test" \
AWS_SECRET_ACCESS_KEY="test" \
AWS_BUCKET="test-bucket" \
RESEND_API_KEY="test" \
python -m pytest tests/ -v --cov=app --cov-report=term-missing
```

---

*Nutrientrena v2.0 — Junio 2026*
