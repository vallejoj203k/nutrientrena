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
    analytics, public, session_logs, client_tasks,
)
from app.routers import settings as settings_router
from app.routers.nutrition import type_food, group_food, aliments, diets, recipes

# ── CORS origins ──────────────────────────────────────────────────────────────
_raw_origins = settings.ALLOWED_ORIGINS
_origins = [o.strip() for o in _raw_origins.split(",")] if _raw_origins != "*" else ["*"]

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url=None,
    openapi_url="/api/openapi.json",
    swagger_ui_parameters={"persistAuthorization": True},
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
app.include_router(session_logs.router, prefix=API_PREFIX)
app.include_router(client_tasks.router, prefix=API_PREFIX)
app.include_router(public.router, prefix=API_PREFIX)
app.include_router(settings_router.router, prefix=API_PREFIX)


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
