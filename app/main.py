import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import settings
from app.core.limiter import limiter
from app.routers import (
    auth, users, roles, menus, parameters, countries,
    muscle_groups, trainings, routines, events, notes, progress, files, forms, checkins, plans,
    analytics, public, session_logs, client_tasks, programs, weekly_menus, client_exercises,
    calendar_tasks, team, organizations, contracts,
)
from app.routers import settings as settings_router
from app.routers.nutrition import type_food, group_food, aliments, diets, recipes, client_aliments, pathologies
from app.routers.chat import router as chat_router, router_ws as chat_ws_router

# ── CORS origins ──────────────────────────────────────────────────────────────
_origins = settings.cors_origins

_tags_metadata = [
    {"name": "Auth", "description": "Autenticación JWT — login, refresh token, recuperación de contraseña."},
    {"name": "Users", "description": "Gestión de usuarios, clientes y coaches."},
    {"name": "Roles", "description": "Roles de usuario y asignación de menús (solo superadmin)."},
    {"name": "Menus", "description": "Menús del sistema para control de acceso."},
    {"name": "Parameters", "description": "Parámetros del sistema (estados, géneros, niveles de actividad)."},
    {"name": "Countries", "description": "Catálogo de países."},
    {"name": "Events", "description": "Eventos del calendario — individuales y recurrentes."},
    {"name": "Type Events", "description": "Tipos de evento para el calendario."},
    {"name": "Routines", "description": "Rutinas de entrenamiento con días, bloques y ejercicios."},
    {"name": "Trainings", "description": "Catálogo de ejercicios."},
    {"name": "Muscle Groups", "description": "Grupos musculares para clasificar ejercicios."},
    {"name": "Check-ins", "description": "Check-ins semanales de clientes con métricas y feedback del coach."},
    {"name": "Progress", "description": "Progreso diario y objetivos físicos del cliente."},
    {"name": "Client Targets", "description": "Objetivos físicos del cliente (peso meta, grasa corporal, etc.)."},
    {"name": "Plans", "description": "Entrega de planes (dieta + rutina) al cliente por email."},
    {"name": "Analytics", "description": "Estadísticas y métricas del negocio para el dashboard."},
    {"name": "Files", "description": "Subida y gestión de archivos en Cloudflare R2."},
    {"name": "Forms - Templates", "description": "Plantillas de formularios de intake para clientes."},
    {"name": "Forms - Assignments", "description": "Asignación y envío de formularios a clientes."},
    {"name": "Public", "description": "Endpoints públicos — formularios sin autenticación para clientes."},
    {"name": "Template Notes", "description": "Plantillas de notas reutilizables para instructores."},
    {"name": "Note Users", "description": "Notas del instructor sobre sus clientes."},
    {"name": "Session Logs", "description": "Registro de sesiones de entrenamiento completadas."},
    {"name": "Client Tasks", "description": "Tareas semanales asignadas a clientes."},
    {"name": "Calendar Tasks", "description": "Tareas y eventos por fecha específica en el calendario del cliente, con soporte de recurrencia."},
    {"name": "Programs", "description": "Programas de entrenamiento con fases y asignación de clientes."},
    {"name": "Weekly Menus", "description": "Menús semanales nutricionales: 7 dietas (una por día) agrupadas como bloque."},
    {"name": "Settings", "description": "Configuración global de la aplicación."},
    {"name": "Nutrition - Aliments", "description": "Catálogo de alimentos con valores nutricionales."},
    {"name": "Nutrition - Diets", "description": "Planes de alimentación con comidas y macros."},
    {"name": "Nutrition - Recipes", "description": "Recetas compuestas por múltiples alimentos."},
    {"name": "Nutrition - TypeFood", "description": "Tipos de alimento (proteína, carbohidrato, grasa, etc.)."},
    {"name": "Nutrition - GroupFood", "description": "Grupos de alimentos (carnes, verduras, lácteos, etc.)."},
    {"name": "Nutrition - Client Aliments", "description": "Alimentos personalizados por cliente creados por el coach."},
    {"name": "Nutrition - Pathologies", "description": "Catálogo de patologías/condiciones asociables a dietas."},
    {"name": "Client Exercises", "description": "Ejercicios personalizados por cliente creados por el coach."},
]

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url=None,
    openapi_url="/api/openapi.json",
    swagger_ui_parameters={"persistAuthorization": True},
    openapi_tags=_tags_metadata,
)

# ── Rate limiting ─────────────────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=_origins != ["*"],   # credentials only when origins are explicit
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-Requested-With"],
)

# ── Security headers ──────────────────────────────────────────────────────────
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response

API_PREFIX = "/api"

app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(users.router, prefix=API_PREFIX)
app.include_router(roles.router, prefix=API_PREFIX)
app.include_router(menus.router, prefix=API_PREFIX)
app.include_router(parameters.router_params, prefix=API_PREFIX)
app.include_router(parameters.router_details, prefix=API_PREFIX)
app.include_router(countries.router, prefix=API_PREFIX)
app.include_router(muscle_groups.router, prefix=API_PREFIX)
app.include_router(trainings.router, prefix=API_PREFIX)
app.include_router(routines.router, prefix=API_PREFIX)
app.include_router(events.router_events, prefix=API_PREFIX)
app.include_router(events.router_type_events, prefix=API_PREFIX)
app.include_router(notes.router_templates, prefix=API_PREFIX)
app.include_router(notes.router_notes, prefix=API_PREFIX)
app.include_router(progress.router_progress, prefix=API_PREFIX)
app.include_router(progress.router_targets, prefix=API_PREFIX)
app.include_router(files.router, prefix=API_PREFIX)
app.include_router(forms.router_templates, prefix=API_PREFIX)
app.include_router(forms.router_assignments, prefix=API_PREFIX)
app.include_router(checkins.router, prefix=API_PREFIX)
app.include_router(plans.router, prefix=API_PREFIX)
app.include_router(analytics.router, prefix=API_PREFIX)
app.include_router(type_food.router, prefix=API_PREFIX)
app.include_router(group_food.router, prefix=API_PREFIX)
app.include_router(aliments.router, prefix=API_PREFIX)
app.include_router(diets.router, prefix=API_PREFIX)
app.include_router(recipes.router, prefix=API_PREFIX)
app.include_router(client_aliments.router, prefix=API_PREFIX)
app.include_router(pathologies.router, prefix=API_PREFIX)
app.include_router(client_exercises.router, prefix=API_PREFIX)
app.include_router(session_logs.router, prefix=API_PREFIX)
app.include_router(client_tasks.router, prefix=API_PREFIX)
app.include_router(calendar_tasks.router, prefix=API_PREFIX)
app.include_router(programs.router, prefix=API_PREFIX)
app.include_router(weekly_menus.router, prefix=API_PREFIX)
app.include_router(public.router, prefix=API_PREFIX)
app.include_router(settings_router.router, prefix=API_PREFIX)
app.include_router(chat_router, prefix=API_PREFIX)
app.include_router(chat_ws_router)
app.include_router(team.router, prefix=API_PREFIX)
app.include_router(organizations.router, prefix=API_PREFIX)
app.include_router(contracts.router, prefix=API_PREFIX)


# ── Global exception handler (no stack traces in production) ──────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    if settings.DEBUG:
        import traceback
        detail = traceback.format_exc()[-2000:]
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": str(exc), "detail": detail},
        )
    return JSONResponse(
        status_code=500,
        content={"success": False, "message": "Error interno del servidor"},
    )


# ── Frontend static files ─────────────────────────────────────────────────────
_frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.isdir(_frontend_dir):
    app.mount("/app", StaticFiles(directory=_frontend_dir, html=True), name="frontend")


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/app/login.html")


@app.get("/api/health")
def health():
    return {"status": "ok", "app": settings.APP_NAME}
