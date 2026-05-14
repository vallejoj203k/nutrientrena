# nutrientrena

Backend FastAPI — migración desde Laravel 9 + Passport.

## Stack

- **FastAPI** + Uvicorn (ASGI)
- **SQLAlchemy 2** + Alembic (ORM + migraciones)
- **MySQL** via PyMySQL
- **JWT** con python-jose + passlib/bcrypt
- **AWS S3** con boto3 (archivos)
- **Pydantic v2** (validación)

## Estructura

```
app/
├── main.py               # Entry point FastAPI
├── config.py             # Settings (pydantic-settings)
├── database.py           # Engine + sesión SQLAlchemy
├── core/
│   ├── security.py       # JWT, hash passwords
│   └── dependencies.py   # get_current_user, require_roles
├── models/               # SQLAlchemy models
│   └── nutrition/
├── schemas/              # Pydantic schemas (request/response)
│   └── nutrition/
├── routers/              # FastAPI routers (1 por módulo)
│   └── nutrition/
└── seeds/                # Seeders de datos iniciales
alembic/                  # Migraciones de base de datos
```

## Instalación

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# editar .env con credenciales de BD y JWT secret

# Crear tablas
alembic upgrade head

# Seedear datos iniciales
python -m app.seeds.run_seeds

# Iniciar servidor
uvicorn app.main:app --reload
```

## Documentación API

Con el servidor corriendo:
- Swagger UI: `http://localhost:8000/api/docs`
- ReDoc: `http://localhost:8000/api/redoc`

## Módulos API

| Prefijo | Descripción |
|---------|-------------|
| `/api/auth` | Login, logout, me, refresh token |
| `/api/users` | Gestión de usuarios/clientes |
| `/api/roles` | Roles y asignación de menús |
| `/api/menus` | Menús del sistema |
| `/api/parameters` | Parámetros del sistema |
| `/api/countries` | Países |
| `/api/muscle-groups` | Grupos musculares |
| `/api/trainings` | Ejercicios |
| `/api/routines` | Rutinas de entrenamiento |
| `/api/typeFood` | Tipos de alimento |
| `/api/groupFood` | Grupos de alimento |
| `/api/aliments` | Alimentos |
| `/api/diets` | Dietas |
| `/api/recipes` | Recetas |
| `/api/client-targets` | Objetivos del cliente |
| `/api/events` | Eventos/calendario |
| `/api/type-events` | Tipos de eventos |
| `/api/template-notes` | Plantillas de notas |
| `/api/note-users` | Notas por usuario |
| `/api/progress-day-users` | Progreso diario |
| `/api/files` | Archivos en AWS S3 |

## Credenciales admin por defecto

- Email: `admin@nutrientrena.com`
- Password: `Admin123!`
