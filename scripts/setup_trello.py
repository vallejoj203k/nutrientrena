"""
Crea las listas y cards del sprint board en Trello.
Uso: python scripts/setup_trello.py
Requiere: pip install requests
"""
import os
import sys

try:
    import requests
except ImportError:
    print("ERROR: instala requests con: pip install requests")
    sys.exit(1)

API_KEY  = os.environ.get("TRELLO_API_KEY", "")
TOKEN    = os.environ.get("TRELLO_TOKEN", "")
BOARD_ID = os.environ.get("TRELLO_BOARD_ID", "")
BASE     = "https://api.trello.com/1"

if not all([API_KEY, TOKEN, BOARD_ID]):
    print("ERROR: define las variables de entorno TRELLO_API_KEY, TRELLO_TOKEN y TRELLO_BOARD_ID")
    print()
    print("Ejemplo en PowerShell:")
    print('  $env:TRELLO_API_KEY="tu_api_key"')
    print('  $env:TRELLO_TOKEN="tu_token"')
    print('  $env:TRELLO_BOARD_ID="tu_board_id"')
    print('  python scripts/setup_trello.py')
    sys.exit(1)

AUTH = {"key": API_KEY, "token": TOKEN}

LISTAS = ["Backlog", "Por Hacer", "En Proceso", "Control de Calidad", "Hecho"]

SPRINTS = {
    "Hecho": [
        {
            "name": "FASE 0 - Infraestructura base",
            "desc": (
                "Proyecto FastAPI + estructura de carpetas\n"
                "SQLAlchemy 2 + Alembic configurado\n"
                "33 tablas migradas a MySQL (Railway)\n"
                "Seeds: roles, parametros, paises, menus, admin\n"
                "JWT auth (login, refresh, me)\n"
                "Desplegado en Railway con dominio .up.railway.app\n"
                "CI/CD GitHub Actions (lint + validacion de modelos)"
            ),
        },
        {
            "name": "Sprint 6 - Routers secundarios",
            "desc": (
                "aliments: UUID id, filtro parent_id, created/updated_user_id\n"
                "group_food / type_food: state -> status\n"
                "roles: generacion automatica de slug al crear"
            ),
        },
        {
            "name": "Sprint 7 - Eventos, Notas, Progreso",
            "desc": (
                "Events / TypeEvents\n"
                "Notes / TemplateNotes\n"
                "ProgressDay / ClientTargets\n"
                "Modelos, schemas y routers consistentes"
            ),
        },
        {
            "name": "Sprint 8 - Recetas",
            "desc": (
                "RecipeDetail.aliment_id: int -> str (UUID)\n"
                "GET /client/{client_id}: endpoint corregido con UserDetail\n"
                "Seed admin_user reescrito (User + UserDetail + RoleUser)"
            ),
        },
    ],
    "Por Hacer": [
        {
            "name": "Sprint 10 - QA Integral",
            "desc": (
                "POST /api/auth/login -> admin@nutrientrena.com / Admin123!\n"
                "GET /api/auth/me -> perfil del admin\n"
                "POST /api/users -> crear cliente\n"
                "POST /api/routines -> crear y asignar rutina\n"
                "POST /api/diets -> crear y asignar dieta\n"
                "POST /api/progress-day-users -> registrar progreso\n"
                "Verificar seeds en Railway (parametros, menus)"
            ),
        },
        {
            "name": "Sprint 11 - Frontend integration",
            "desc": (
                "Conectar frontend con API en Railway\n"
                "Configurar CORS para dominio del frontend\n"
                "Probar flujo completo login -> dashboard"
            ),
        },
    ],
    "Backlog": [
        {
            "name": "Sprint 12 - Upload de imagenes",
            "desc": (
                "Configurar AWS S3 bucket en produccion\n"
                "Probar POST /api/files/external\n"
                "Integrar upload en perfil de usuario y alimentos"
            ),
        },
        {
            "name": "Sprint 13 - Email / Recuperar contrasena",
            "desc": (
                "Configurar SMTP (MAIL_HOST, MAIL_USER, etc.)\n"
                "Implementar envio real en /api/auth/recover-password\n"
                "Template de email HTML"
            ),
        },
        {
            "name": "Sprint 14 - PDF de dietas",
            "desc": (
                "Implementar generacion real de PDF en GET /api/diets/{id}/pdf\n"
                "Template con macros, alimentos por comida\n"
                "Descarga directa o link S3"
            ),
        },
    ],
}


def crear_lista(nombre):
    r = requests.post(f"{BASE}/lists", params={**AUTH, "name": nombre, "idBoard": BOARD_ID})
    if r.status_code != 200:
        print(f"      ERROR al crear lista '{nombre}': {r.status_code} - {r.text}")
        return None
    return r.json()["id"]


def crear_card(nombre, desc, lista_id):
    r = requests.post(f"{BASE}/cards", params={**AUTH, "name": nombre, "desc": desc, "idList": lista_id})
    if r.status_code != 200:
        print(f"      ERROR al crear card '{nombre}': {r.status_code} - {r.text}")


def main():
    # Obtener el ID largo del board (necesario para crear listas)
    rb = requests.get(f"{BASE}/boards/{BOARD_ID}", params=AUTH)
    if rb.status_code != 200:
        print(f"ERROR al conectar con el board: {rb.status_code} - {rb.text}")
        return
    board_real_id = rb.json()["id"]
    print(f"Board ID: {board_real_id}")

    print("Obteniendo listas del board...")
    r = requests.get(f"{BASE}/boards/{board_real_id}/lists", params=AUTH)
    if r.status_code != 200:
        print(f"ERROR al obtener listas: {r.status_code} - {r.text}")
        return

    existentes = r.json()
    lista_ids = {l["name"]: l["id"] for l in existentes}

    for nombre in LISTAS:
        if nombre not in lista_ids:
            print(f"   Creando lista: {nombre}")
            rr = requests.post(f"{BASE}/lists", params={**AUTH, "name": nombre, "idBoard": board_real_id})
            if rr.status_code != 200:
                print(f"      ERROR: {rr.status_code} - {rr.text}")
            else:
                lista_ids[nombre] = rr.json()["id"]
        else:
            print(f"   Lista ya existe: {nombre}")

    print("\nCreando cards...")
    for lista_nombre, cards in SPRINTS.items():
        if lista_nombre not in lista_ids:
            print(f"   SKIP: lista '{lista_nombre}' no encontrada")
            continue
        lista_id = lista_ids[lista_nombre]
        for card in cards:
            print(f"   [{lista_nombre}] {card['name']}")
            crear_card(card["name"], card["desc"], lista_id)

    print(f"\nListo: https://trello.com/b/{BOARD_ID}")


if __name__ == "__main__":
    main()
