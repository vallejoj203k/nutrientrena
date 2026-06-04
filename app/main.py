import os
import traceback

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.routers import (
    auth, users, roles, menus, parameters, countries,
    muscle_groups, trainings, routines, events, notes, progress, files, forms, checkins, plans,
    analytics, public, session_logs, client_tasks,
)
from app.routers import settings as settings_router
from app.routers.nutrition import type_food, group_food, aliments, diets, recipes

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url=None,
    openapi_url="/api/openapi.json",
    swagger_ui_parameters={"persistAuthorization": True},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    tb = traceback.format_exc()
    return JSONResponse(
        status_code=500,
        content={"success": False, "message": str(exc), "detail": tb[-2000:]},
    )


_frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.isdir(_frontend_dir):
    app.mount("/app", StaticFiles(directory=_frontend_dir, html=True), name="frontend")


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/app/login.html")


@app.get("/api/health")
def health():
    return {"status": "ok", "app": settings.APP_NAME}
