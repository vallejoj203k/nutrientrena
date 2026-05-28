# Nutrientrena — Backend API + Frontend

Plataforma de gestión de clientes, planes de entrenamiento y nutrición para coaches y nutricionistas.

---

## Acceso rápido

| Recurso | URL |
|---------|-----|
| **Aplicación web** | https://nutrientrena-production.up.railway.app/app/login.html |
| **Dashboard** | https://nutrientrena-production.up.railway.app/app/dashboard.html |
| **Swagger (API docs)** | https://nutrientrena-production.up.railway.app/api/docs |
| **Health check** | https://nutrientrena-production.up.railway.app/api/health |

---

## Stack tecnológico

| Tecnología | Uso |
|------------|-----|
| **FastAPI** | Framework principal de la API |
| **SQLAlchemy 2** | ORM para base de datos |
| **Alembic** | Migraciones de base de datos |
| **MySQL** (Railway) | Base de datos en producción |
| **JWT** (python-jose) | Autenticación segura |
| **Resend SDK** | Envío de emails transaccionales |
| **Cloudflare R2** | Almacenamiento de imágenes (S3-compatible) |
| **WeasyPrint** | Generación de PDFs de dietas y rutinas |
| **Pydantic v2** | Validación de datos |
| **GitHub Actions** | CI/CD automático |
| **HTML/CSS/JS** | Frontend puro sin frameworks externos |

---

## Cómo autenticarse

Todos los endpoints (excepto `/api/auth/login`, recuperar contraseña y `/api/public/*`) requieren un token JWT.

**Paso 1 — Obtener token:**
```
POST /api/auth/login
{ "email": "vallejoj203k@gmail.com", "password": "Admin123!" }
```
La respuesta incluye `data.token`.

**Paso 2 — Usar el token:**
```
Authorization: Bearer <token>
```

**En Swagger:** clic en **Authorize** (candado arriba a la derecha), pegar el token y confirmar.

> El token expira en 60 minutos. Usar `PUT /api/auth/refresh-token` para renovarlo.

---

## Frontend — Páginas disponibles

| Página | URL | Descripción |
|--------|-----|-------------|
| Login | `/app/login.html` | Autenticación con JWT |
| Reset password | `/app/reset-password.html` | Recuperar contraseña |
| Dashboard | `/app/dashboard.html` | Estadísticas generales y preview kanban |
| Kanban | `/app/kanban.html` | Pipeline de clientes con drag & drop |
| Clientes | `/app/clients.html` | Lista, búsqueda, filtros, exportar CSV |
| Perfil cliente | `/app/client-profile.html?id={uuid}` | Tabs: Resumen · Formulario · Entregas · Comercial |
| Check-ins | `/app/checkins.html` | Historial semanal con mediciones corporales |
| Formularios | `/app/forms.html` | Plantillas de intake y gestión de asignaciones |
| Dietas | `/app/diets.html` | Creación de dietas, macros, alimentos, PDF, clonar |
| Rutinas | `/app/routines.html` | Creación de rutinas por días, PDF, clonar |
| Analytics | `/app/analytics.html` | Métricas, gráficos SVG, rendimiento por coach |
| Catálogos nutrición | `/app/nutrition-catalog.html` | Tipos y grupos de alimentos |
| Formulario público | `/app/public/form.html?id={uuid}` | Formulario para clientes sin login |

---

## Módulos de la API

### Autenticación (`/api/auth`)

| Endpoint | Método | Auth | Descripción |
|----------|--------|------|-------------|
| `/api/auth/login` | POST | ❌ | Iniciar sesión, devuelve token JWT |
| `/api/auth/me` | GET | ✅ | Perfil del usuario autenticado |
| `/api/auth/refresh-token` | PUT | ✅ | Renovar token |
| `/api/auth/logout` | POST | ✅ | Cerrar sesión |
| `/api/auth/recover-password` | POST | ❌ | Email de recuperación |
| `/api/auth/menus` | GET | ✅ | Menús disponibles según rol |

---

### Usuarios y Clientes (`/api/users`)

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/users` | POST | Crear usuario/cliente |
| `/api/users/{slug}/findAll` | GET | Listar usuarios de un rol |
| `/api/users/{slug}/search` | GET | Buscar con paginación y filtros |
| `/api/users/{id}/edit` | GET | Ver perfil completo |
| `/api/users/{id}/update` | PUT | Actualizar datos + campos CRM |
| `/api/users/{id}/change` | PUT | Cambiar estado del cliente |
| `/api/users/kanban` | GET | Clientes agrupados por estado |
| `/api/users/assign` | POST | Asignar cliente a coach |

**Roles disponibles:**

| ID | Slug | Nombre |
|----|------|--------|
| 1 | superadmin | Superadministrador |
| 2 | admin | Administrador |
| 3 | setter | Setter |
| 4 | closer | Closer |
| 5 | coach | Coach |
| 6 | client | Cliente |

**Campos CRM en perfil** (guardados en `user_details`):
`plan_comprado`, `precio`, `estado_pago`, `importe_pagado`, `importe_pendiente`, `metodo_pago`, `fecha_compra`, `fecha_limite_entrega`, `responsable_venta`, `crm_origen`, `whatsapp_link`, `consentimiento_evolucion`

---

### Check-ins Semanales (`/api/checkins`)

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/checkins` | POST | Registrar check-in con mediciones corporales |
| `/api/checkins/client/{id}` | GET | Historial + delta de peso semana a semana |
| `/api/checkins/summary/{id}` | GET | Cambio total de peso desde el inicio |
| `/api/checkins/{id}/coach-notes` | PUT | Notas del coach + actualizar mediciones |
| `/api/checkins/{id}` | DELETE | Eliminar check-in |

**Campos de medición disponibles:** `weight`, `body_fat`, `waist`, `chest`, `hips`, `arms`, `legs`, `photo_url`

---

### Entrega de Planes (`/api/plans`)

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/plans/deliver` | POST | Entregar dieta + rutina al cliente por email |
| `/api/plans/history/{client_id}` | GET | Historial de entregas con nombres de dieta/rutina |
| `/api/plans/resend/{delivery_id}` | POST | Reenviar email de una entrega anterior |

```json
POST /api/plans/deliver
{
  "client_user_detail_id": "uuid",
  "diet_id": "uuid",         
  "routine_id": 1,           
  "message": "Mensaje del coach",
  "loom_link": "https://loom.com/...",
  "send_email": true
}
```

---

### Formularios de Intake (`/api/form-templates`, `/api/form-assignments`)

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/form-templates` | GET | Listar plantillas |
| `/api/form-templates` | POST | Crear plantilla con campos |
| `/api/form-templates/{id}` | PUT | Editar plantilla |
| `/api/form-templates/{id}` | DELETE | Eliminar plantilla |
| `/api/form-templates/default` | GET | Plantilla por defecto (18 campos) |
| `/api/form-assignments` | POST | Asignar formulario a cliente |
| `/api/form-assignments/pending` | GET | Formularios pendientes de respuesta |
| `/api/form-assignments/pending-count` | GET | Conteo de pendientes (badge) |
| `/api/form-assignments/client/{id}` | GET | Formulario de un cliente |
| `/api/form-assignments/{id}/submit` | POST | Cliente envía respuestas |
| `/api/form-assignments/{id}/responses` | GET | Ver respuestas guardadas |

### Formulario público — sin autenticación (`/api/public`)

| Endpoint | Método | Auth | Descripción |
|----------|--------|------|-------------|
| `/api/public/form/{assignment_id}` | GET | ❌ | Obtener template + estado del formulario |
| `/api/public/form/{assignment_id}/submit` | POST | ❌ | Cliente envía respuestas desde el email |

> Al enviar, peso, altura, teléfono, género, objetivo y nivel de actividad se sincronizan al perfil del cliente.

---

### Analytics (`/api/analytics`)

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/analytics/overview` | GET | Total clientes, activos, nuevos este mes, coaches, check-ins |
| `/api/analytics/states` | GET | Distribución de clientes por estado (%) |
| `/api/analytics/checkins` | GET | Adherencia, cambio de peso promedio, tendencia 8 semanas |
| `/api/analytics/coaches` | GET | Clientes y check-ins por coach |

Todos soportan filtro `?coach_id=uuid`.

---

### Archivos e Imágenes (`/api/files`)

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/files/upload` | POST | Subir imagen → devuelve URL pública (Cloudflare R2) |
| `/api/files/delete` | DELETE | Eliminar archivo por key |
| `/api/files/list` | GET | Listar archivos de una carpeta |

Límite: **10 MB** · Formatos: JPG, PNG, WEBP, GIF  
Carpetas: `profiles`, `checkins`, `aliments`, `uploads`

---

### Nutrición

#### Dietas (`/api/diets`)

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/diets/findAll` | GET | Todas las dietas del coach |
| `/api/diets` | POST | Crear dieta con macros y alimentos |
| `/api/diets/{id}` | PUT | Actualizar dieta |
| `/api/diets/{id}` | DELETE | Eliminar dieta |
| `/api/diets/{id}/pdf` | GET | Descargar PDF de la dieta |
| `/api/diets/clone` | POST | Clonar dieta existente |
| `/api/diets/{client_id}/assigned` | POST | Asignar dieta a cliente |
| `/api/diets/client/{client_id}` | GET | Dietas asignadas a un cliente |

#### Catálogos (`/api/typeFood`, `/api/groupFood`)

| Endpoint | Descripción |
|----------|-------------|
| `GET /api/typeFood/findAll` | Todos los tipos activos |
| `POST /api/typeFood` | Crear tipo |
| `PUT /api/typeFood/{id}/update` | Editar / desactivar |
| `GET /api/groupFood/findAll` | Todos los grupos activos |
| `POST /api/groupFood` | Crear grupo |
| `PUT /api/groupFood/{id}/update` | Editar / desactivar |

#### Alimentos y Recetas

| Módulo | Prefijo | Descripción |
|--------|---------|-------------|
| Alimentos | `/api/aliments` | CRUD + importación masiva CSV |
| Recetas | `/api/recipes` | CRUD + asignación a cliente |

---

### Entrenamiento

| Módulo | Prefijo | Descripción |
|--------|---------|-------------|
| Rutinas | `/api/routines` | CRUD + días + PDF + clonar |
| Grupos musculares | `/api/muscle-groups` | Catálogo |
| Ejercicios | `/api/trainings` | Biblioteca de ejercicios |

---

### Seguimiento

| Módulo | Prefijo | Descripción |
|--------|---------|-------------|
| Objetivos / Metas | `/api/client-targets` | Peso objetivo del cliente |
| Progreso diario | `/api/progress-day-users` | Registro diario |
| Eventos | `/api/events` | Calendario de sesiones |
| Notas | `/api/note-users` | Notas del coach al cliente |

---

## Base de datos

**38 tablas en MySQL** desplegadas en Railway. Migraciones con Alembic.

Migraciones aplicadas en producción:

| Revisión | Descripción |
|----------|-------------|
| `bb298e505f5b` | Schema inicial — todas las tablas base |
| `a1b2c3d4e5f6` | Módulo de formularios de intake |
| `b2c3d4e5f6a7` | Tabla weekly_checkins |
| `c3d4e5f6a7b8` | Campos CRM en user_details |
| `d4e5f6a7b8c9` | Tabla plan_deliveries |
| `e5f6a7b8c9d0` | Mediciones corporales en weekly_checkins |

```bash
alembic upgrade head
python -m app.seeds.run_seeds
```

---

## Variables de entorno

| Variable | Descripción |
|----------|-------------|
| `MYSQL_URL` | URL de conexión a MySQL |
| `SECRET_KEY` | Clave secreta para JWT |
| `RESEND_API_KEY` | API key de Resend (emails) |
| `MAIL_FROM` | Dirección de envío de emails |
| `ADMIN_EMAIL` | Email del administrador inicial |
| `FRONTEND_URL` | URL pública del frontend (para links en emails) |
| `R2_ENDPOINT_URL` | Endpoint de Cloudflare R2 |
| `R2_ACCESS_KEY_ID` | Access key de R2 |
| `R2_SECRET_ACCESS_KEY` | Secret key de R2 |
| `R2_BUCKET_NAME` | Nombre del bucket |
| `R2_PUBLIC_URL` | URL pública del bucket |

---

## Instalación local

```bash
git clone https://github.com/vallejoj203k/nutrientrena.git
cd nutrientrena

python -m venv venv
source venv/bin/activate        # Mac/Linux
venv\Scripts\activate           # Windows

pip install -r requirements.txt

cp .env.example .env
# Editar .env con credenciales

alembic upgrade head
python -m app.seeds.run_seeds

uvicorn app.main:app --reload
```

Servidor en `http://localhost:8000` — Swagger en `http://localhost:8000/api/docs`.

---

## Estructura del proyecto

```
app/
├── main.py               # Entry point, routers, archivos estáticos
├── config.py             # Variables de entorno
├── database.py           # Conexión SQLAlchemy
├── core/
│   ├── security.py       # JWT y hash de contraseñas
│   ├── dependencies.py   # require_role_ids, verify_client_access
│   ├── email.py          # Emails transaccionales (Resend)
│   └── responses.py      # send_response / send_error
├── models/               # Modelos SQLAlchemy (38 tablas)
├── schemas/              # Schemas Pydantic v2
├── routers/
│   ├── auth.py, users.py, checkins.py, plans.py
│   ├── forms.py, analytics.py, files.py, public.py
│   ├── routines.py, progress.py, ...
│   └── nutrition/
│       ├── diets.py, aliments.py, recipes.py
│       ├── type_food.py, group_food.py
│       └── ...
├── pdf/                  # Generación de PDFs (WeasyPrint)
└── seeds/                # Datos iniciales idempotentes
alembic/
└── versions/             # 6 migraciones aplicadas
frontend/
├── login.html, dashboard.html, kanban.html
├── clients.html, client-profile.html
├── checkins.html, forms.html, analytics.html
├── diets.html, routines.html
├── nutrition-catalog.html
└── public/
    └── form.html         # Formulario sin login para clientes
scripts/
├── qa_forms.py           # QA Fase 1 (16 checks)
├── qa_fase2_3.py         # QA Fase 2 + 3 (checks automatizados)
└── setup_trello.py       # Sincronización del board Trello
```

---

## CI/CD

Cada push a `main` ejecuta en GitHub Actions:

1. **Lint** con `ruff`
2. **Validación de modelos** — tablas registradas
3. **Validación de rutas** — endpoints registrados
4. **Validación de migraciones** — archivos de migración

---

## Estado del proyecto

| Fase | Descripción | Estado |
|------|-------------|--------|
| **Fase 0** | Infraestructura, auth, roles, seeds, CI/CD, deploy en Railway | ✅ Completa |
| **Fase 1** | Clientes, kanban, check-ins, planes, formularios, frontend base | ✅ Completa |
| **Fase 2** | Analytics, imágenes R2, PDFs, frontend avanzado, roles, emails, CRM | ✅ Completa |
| **Fase 3** | Nutrición completa, mediciones, portal público, perfil extendido | 🔄 En proceso |

### Fase 3 — Detalle

| Ítem | Estado |
|------|--------|
| Portal público para clientes (formulario sin login) | ✅ |
| Perfil cliente extendido (4 tabs + CRM) | ✅ |
| Check-ins con 7 mediciones corporales | ✅ |
| UX de entregas (nombres reales, re-enviar, preview macros) | ✅ |
| Catálogos de nutrición (Tipos + Grupos) | ✅ |
| Alimentos: CRUD + importación masiva CSV | 🔄 |
| Recetas: CRUD + asignación a cliente | 🔄 |
| Metas del cliente (peso objetivo vs actual) | 🔄 |

---

*Nutrientrena v2.0 — Mayo 2026*
