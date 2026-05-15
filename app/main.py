from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer

from app.config import settings
from app.routers import (
    auth, users, roles, menus, parameters, countries,
    muscle_groups, trainings, routines, events, notes, progress, files,
)
from app.routers.nutrition import type_food, group_food, aliments, diets, recipes

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
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
app.include_router(type_food.router, prefix=API_PREFIX)
app.include_router(group_food.router, prefix=API_PREFIX)
app.include_router(aliments.router, prefix=API_PREFIX)
app.include_router(diets.router, prefix=API_PREFIX)
app.include_router(recipes.router, prefix=API_PREFIX)


@app.get("/api/health")
def health():
    return {"status": "ok", "app": settings.APP_NAME}
