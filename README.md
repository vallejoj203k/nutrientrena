# Nutrientrena — Backend API + Frontend

Plataforma de gestión de clientes, planes de entrenamiento y nutrición para coaches y nutricionistas.

---

## Acceso rápido

| Recurso | URL |
|---------|-----|
| **Aplicación web** | https://nutrientrena-production.up.railway.app |
| **Swagger (API docs)** | https://nutrientrena-production.up.railway.app/api/docs |
| **Health check** | https://nutrientrena-production.up.railway.app/api/health |
| **Login frontend** | https://nutrientrena-production.up.railway.app/app/login.html |
| **Dashboard** | https://nutrientrena-production.up.railway.app/app/dashboard.html |

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
| **Pydantic v2** | Validación de datos |
| **GitHub Actions** | CI/CD automático |
| **HTML/CSS/JS** | Frontend puro sin frameworks |

---

## Cómo autenticarse

Todos los endpoints (excepto login y recuperar contraseña) requieren un token JWT.

**Paso 1 — Obtener token:**
```
POST /api/auth/login
{
  "email": "vallejoj203k@gmail.com",
  "password": "Admin123!"
}
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
| Dashboard | `/app/dashboard.html` | Estadísticas generales y preview kanban |
| Kanban | `/app/kanban.html` | Clientes agrupados por estado con drag & drop |
| Clientes | `/app/clients.html` | Lista, búsqueda, filtros y creación de clientes |
| Perfil cliente | `/app/client-profile.html?id={uuid}` | Datos, check-ins, gráfico de peso, entregar plan |
| Check-ins | `/app/checkins.html` | Historial semanal de peso y notas por cliente |
| Formularios | `/app/forms.html` | Plantillas de intake, asignación y respuestas |

---

## Módulos de la API

### Autenticación (`/api/auth`)

| Endpoint | Método | Auth | Descripción |
|----------|--------|------|-------------|
| `/api/auth/login` | POST | ❌ | Iniciar sesión, devuelve token JWT |
| `/api/auth/me` | GET | ✅ | Perfil del usuario autenticado |
| `/api/auth/refresh-token` | PUT | ✅ | Renovar token |
| `/api/auth/logout` | POST | ✅ | Cerrar sesión |
| `/api/auth/recover-password` | POST | ❌ | Email de recuperación de contraseña |
| `/api/auth/menus` | GET | ✅ | Menús disponibles según rol |

---

### Usuarios y Clientes (`/api/users`)

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/users` | POST | Crear usuario/cliente |
| `/api/users/{slug}/findAll` | GET | Listar usuarios de un rol |
| `/api/users/{slug}/search` | GET | Buscar con paginación |
| `/api/users/{id}/edit` | GET | Ver perfil completo |
| `/api/users/{id}/update` | PUT | Actualizar datos |
| `/api/users/{id}/change` | PUT | Cambiar estado del cliente |
| `/api/users/kanban` | GET | Clientes agrupados por estado |
| `/api/users/assign` | POST | Asignar cliente a coach |
| `/api/users/weeks` | POST | Definir semanas de entrenamiento |
| `/api/users/report` | GET | Reporte total de usuarios |

**Roles disponibles:**

| ID | Slug | Nombre |
|----|------|--------|
| 1 | superadmin | Superadministrador |
| 2 | admin | Administrador |
| 3 | setter | Setter |
| 4 | closer | Closer |
| 5 | coach | Coach |
| 6 | client | Cliente |

---

### Kanban (`/api/users/kanban`)

```
GET /api/users/kanban
GET /api/users/kanban?coach_id=<uuid>   → solo clientes de ese coach
```

Respuesta:
```json
{
  "total_clients": 5,
  "columns": [
    { "status_id": 4, "status_name": "Formulario pendiente", "total": 2, "clients": [...] }
  ]
}
```

Mover cliente de columna:
```
PUT /api/users/{id}/change
{ "status_id": <nuevo_estado> }
```

Los 15 estados del cliente se consultan en `GET /api/parameters/search?q=Estado+del+Cliente`.

---

### Formularios de Intake (`/api/form-templates`, `/api/form-assignments`)

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/form-templates` | GET | Listar plantillas |
| `/api/form-templates` | POST | Crear plantilla con campos |
| `/api/form-templates/{id}` | PUT | Editar plantilla |
| `/api/form-templates/{id}` | DELETE | Eliminar plantilla |
| `/api/form-templates/default` | GET | Plantilla por defecto |
| `/api/form-assignments` | POST | Asignar formulario a cliente |
| `/api/form-assignments/pending` | GET | Formularios pendientes |
| `/api/form-assignments/client/{id}` | GET | Formulario de un cliente |
| `/api/form-assignments/{id}/submit` | POST | Cliente envía respuestas |
| `/api/form-assignments/{id}/responses` | GET | Ver respuestas guardadas |

> Al enviar el formulario, peso, altura, teléfono, género, objetivo y nivel de actividad se sincronizan automáticamente al perfil del cliente.

---

### Check-ins Semanales (`/api/checkins`)

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/checkins` | POST | Registrar check-in (peso + notas) |
| `/api/checkins/client/{id}` | GET | Historial de check-ins + delta de peso |
| `/api/checkins/summary/{id}` | GET | Cambio total de peso desde el inicio |
| `/api/checkins/{id}/coach-notes` | PUT | Agregar notas del coach |
| `/api/checkins/{id}` | DELETE | Eliminar check-in |

---

### Entrega de Planes (`/api/plans`)

```
POST /api/plans/deliver
{
  "client_user_detail_id": "uuid-del-cliente",
  "diet_id": "uuid-de-la-dieta",     (opcional)
  "routine_id": 1,                    (opcional)
  "message": "Mensaje del coach..."   (opcional)
}
```

El email incluye macros (kcal, proteínas, carbos, grasas), días de rutina y mensaje personalizado. El estado del cliente cambia automáticamente a **"Plan entregado"**.

---

### Nutrición

| Módulo | Prefijo | Descripción |
|--------|---------|-------------|
| Alimentos | `/api/aliments` | CRUD con UUID |
| Tipos de alimento | `/api/typeFood` | Categorías |
| Grupos de alimento | `/api/groupFood` | Grupos alimenticios |
| Recetas | `/api/recipes` | Recetas con ingredientes |
| Dietas | `/api/diets` | Planes de alimentación completos |

---

### Entrenamiento

| Módulo | Prefijo | Descripción |
|--------|---------|-------------|
| Grupos musculares | `/api/muscle-groups` | CRUD |
| Ejercicios | `/api/trainings` | Biblioteca de ejercicios |
| Rutinas | `/api/routines` | Planes por días |

---

### Seguimiento

| Módulo | Prefijo | Descripción |
|--------|---------|-------------|
| Progreso diario | `/api/progress-day-users` | Registro diario |
| Objetivos | `/api/client-targets` | Peso objetivo y metas |
| Eventos | `/api/events` | Calendario de sesiones |
| Notas | `/api/note-users` | Notas del coach al cliente |

---

### Configuración del sistema

| Módulo | Prefijo | Descripción |
|--------|---------|-------------|
| Roles | `/api/roles` | Roles y permisos de menú |
| Menús | `/api/menus` | Menús del panel por rol |
| Parámetros | `/api/parameters` | Estados, géneros, etc. |
| Países | `/api/countries` | Catálogo de países |

---

## Base de datos

**38 tablas en MySQL** desplegadas en Railway. Migraciones con Alembic.

```bash
# Aplicar migraciones
alembic upgrade head

# Sembrar datos iniciales (roles, parámetros, admin)
python -m app.seeds.run_seeds
```

---

## Variables de entorno

| Variable | Descripción |
|----------|-------------|
| `MYSQL_URL` | URL de conexión a MySQL |
| `SECRET_KEY` | Clave secreta para JWT |
| `RESEND_API_KEY` | API key de Resend |
| `MAIL_FROM` | Dirección de envío de emails |
| `ADMIN_EMAIL` | Email del administrador inicial |
| `FRONTEND_URL` | URL del frontend |

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

Servidor en `http://localhost:8000` — redirige a `http://localhost:8000/api/docs`.

---

## Estructura del proyecto

```
app/
├── main.py               # Entry point, routers y archivos estáticos
├── config.py             # Variables de entorno
├── database.py           # Conexión SQLAlchemy
├── core/
│   ├── security.py       # JWT y hash de contraseñas
│   ├── dependencies.py   # get_current_user
│   ├── email.py          # Envío de emails (Resend)
│   └── responses.py      # Formato estándar de respuestas
├── models/               # Modelos SQLAlchemy (38 tablas)
├── schemas/              # Schemas Pydantic
├── routers/              # Endpoints por módulo
└── seeds/                # Datos iniciales
alembic/
└── versions/             # Archivos de migración
frontend/
├── login.html            # Página de login
├── dashboard.html        # Dashboard principal
├── kanban.html           # Vista kanban con drag & drop
├── clients.html          # Lista de clientes
├── client-profile.html   # Perfil detallado del cliente
├── checkins.html         # Check-ins semanales
└── forms.html            # Formularios de intake
scripts/
├── qa_forms.py           # Script QA automatizado (16 checks)
└── setup_trello.py       # Configuración del board Trello
```

---

## CI/CD

Cada push ejecuta en GitHub Actions:

1. **Lint** con `ruff`
2. **Validación de modelos** — 38 tablas registradas
3. **Validación de rutas** — endpoints registrados
4. **Validación de migraciones** — archivos de migración existentes

---

## Estado del proyecto

| Fase | Descripción | Estado |
|------|-------------|--------|
| **Fase 0** | Infraestructura, auth, roles, seeds, CI/CD, deploy | ✅ Completa |
| **Fase 1** | Clientes, kanban, check-ins, planes, formularios, frontend | ✅ Completa |
| **Fase 2** | Analíticas, upload de imágenes, PDF | 🔜 Pendiente |

---

*Nutrientrena v1.0 — Mayo 2026*
