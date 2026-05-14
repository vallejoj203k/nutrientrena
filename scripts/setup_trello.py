"""
Crea las listas y cards del sprint board en Trello.
Uso:
    TRELLO_API_KEY=xxx TRELLO_TOKEN=yyy TRELLO_BOARD_ID=zzz python scripts/setup_trello.py
"""
import os
import sys
import urllib.request
import urllib.parse
import json

API_KEY  = os.environ.get("TRELLO_API_KEY", "")
TOKEN    = os.environ.get("TRELLO_TOKEN", "")
BOARD_ID = os.environ.get("TRELLO_BOARD_ID", "")
BASE     = "https://api.trello.com/1"

if not all([API_KEY, TOKEN, BOARD_ID]):
    print("ERROR: define TRELLO_API_KEY, TRELLO_TOKEN y TRELLO_BOARD_ID como variables de entorno.")
    sys.exit(1)


def api(method, path, **params):
    params.update(key=API_KEY, token=TOKEN)
    url = f"{BASE}{path}"
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(url, data=data if method == "POST" else None, method=method)
    if method in ("PUT", "DELETE"):
        req = urllib.request.Request(f"{url}?{urllib.parse.urlencode(params)}", method=method)
    elif method == "GET":
        url = f"{url}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


# ── Definición del board ──────────────────────────────────────────────────────

LISTAS = ["Backlog", "Por Hacer", "En Proceso", "Control de Calidad", "Hecho"]

SPRINTS = {
    "Hecho": [
        {
            "name": "FASE 0 — Infraestructura base",
            "desc": (
                "✅ Proyecto FastAPI + estructura de carpetas\n"
                "✅ SQLAlchemy 2 + Alembic configurado\n"
                "✅ 33 tablas migradas a MySQL (Railway)\n"
                "✅ Seeds: roles, parámetros, países, menús, admin\n"
                "✅ JWT auth (login, refresh, me)\n"
                "✅ Desplegado en Railway con dominio .up.railway.app\n"
                "✅ CI/CD GitHub Actions (lint + validación de modelos)"
            ),
        },
        {
            "name": "Sprint 6 — Routers secundarios",
            "desc": (
                "✅ aliments: UUID id, filtro parent_id, created/updated_user_id\n"
                "✅ group_food / type_food: state → status\n"
                "✅ roles: generación automática de slug al crear"
            ),
        },
        {
            "name": "Sprint 7 — Eventos, Notas, Progreso",
            "desc": (
                "✅ Events / TypeEvents\n"
                "✅ Notes / TemplateNotes\n"
                "✅ ProgressDay / ClientTargets\n"
                "✅ Modelos, schemas y routers consistentes"
            ),
        },
        {
            "name": "Sprint 8 — Recetas",
            "desc": (
                "✅ RecipeDetail.aliment_id: int → str (UUID)\n"
                "✅ /client/{client_id}: endpoint corregido con UserDetail\n"
                "✅ Seed admin_user reescrito (User + UserDetail + RoleUser)"
            ),
        },
    ],
    "Por Hacer": [
        {
            "name": "Sprint 10 — QA Integral",
            "desc": (
                "🔲 POST /api/auth/login → admin@nutrientrena.com / Admin123!\n"
                "🔲 GET /api/auth/me → perfil del admin\n"
                "🔲 POST /api/users → crear cliente\n"
                "🔲 POST /api/routines → crear y asignar rutina\n"
                "🔲 POST /api/diets → crear y asignar dieta\n"
                "🔲 POST /api/progress-day-users → registrar progreso\n"
                "🔲 Verificar seeds en Railway (parámetros, menús)"
            ),
        },
        {
            "name": "Sprint 11 — Frontend integration",
            "desc": (
                "🔲 Conectar frontend con API en Railway\n"
                "🔲 Configurar CORS para dominio del frontend\n"
                "🔲 Probar flujo completo login → dashboard"
            ),
        },
    ],
    "Backlog": [
        {
            "name": "Sprint 12 — Upload de imágenes",
            "desc": (
                "🔲 Configurar AWS S3 bucket en producción\n"
                "🔲 Probar POST /api/files/external\n"
                "🔲 Integrar upload en perfil de usuario y alimentos"
            ),
        },
        {
            "name": "Sprint 13 — Email / Recuperar contraseña",
            "desc": (
                "🔲 Configurar SMTP (MAIL_HOST, MAIL_USER, etc.)\n"
                "🔲 Implementar envío real en /api/auth/recover-password\n"
                "🔲 Template de email HTML"
            ),
        },
        {
            "name": "Sprint 14 — PDF de dietas",
            "desc": (
                "🔲 Implementar generación real de PDF en GET /api/diets/{id}/pdf\n"
                "🔲 Template con macros, alimentos por comida\n"
                "🔲 Descarga directa o link S3"
            ),
        },
    ],
}


def main():
    # 1. Obtener listas existentes
    print("📋 Obteniendo listas del board...")
    existentes = api("GET", f"/boards/{BOARD_ID}/lists")
    lista_ids = {l["name"]: l["id"] for l in existentes}

    # 2. Crear listas que falten
    for nombre in LISTAS:
        if nombre not in lista_ids:
            print(f"   ➕ Creando lista: {nombre}")
            result = api("POST", "/lists", name=nombre, idBoard=BOARD_ID)
            lista_ids[nombre] = result["id"]
        else:
            print(f"   ✓ Lista ya existe: {nombre}")

    # 3. Crear cards
    print("\n🃏 Creando cards...")
    for lista_nombre, cards in SPRINTS.items():
        lista_id = lista_ids[lista_nombre]
        for card in cards:
            print(f"   ➕ [{lista_nombre}] {card['name']}")
            api("POST", "/cards", name=card["name"], desc=card["desc"], idList=lista_id)

    print("\n✅ Board configurado:")
    print(f"   https://trello.com/b/{BOARD_ID}")


if __name__ == "__main__":
    main()
