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
    # ─────────────────────────────────────────────────────────────────────────
    # HECHO
    # ─────────────────────────────────────────────────────────────────────────
    "Hecho": [
        {
            "name": "FASE 0 - Infraestructura base",
            "desc": (
                "✅ Proyecto FastAPI + estructura de carpetas (app/routers, models, schemas, seeds)\n"
                "✅ SQLAlchemy 2 + Alembic configurado\n"
                "✅ 37 tablas migradas a MySQL (Railway)\n"
                "✅ Seeds idempotentes: roles(6), parametros, paises, menus, admin\n"
                "✅ JWT auth: login, refresh, logout, /me\n"
                "✅ Recuperar contraseña via Resend SDK\n"
                "✅ HTTPBearer en Swagger (token sin prefijo Bearer)\n"
                "✅ Desplegado en Railway con dominio .up.railway.app\n"
                "✅ CI/CD GitHub Actions: lint ruff + validacion modelos + validacion rutas"
            ),
        },
        {
            "name": "Sprint 1-5 - Modelos y migraciones base",
            "desc": (
                "✅ 33 tablas base: users, user_details, roles, role_user, parameters, parameter_details\n"
                "✅ countries, menus, menu_role\n"
                "✅ aliments, aliment_descriptions, type_foods, group_foods\n"
                "✅ recipes, recipe_details\n"
                "✅ diets, diet_details, diet_foods, diet_food_aliments\n"
                "✅ routines, routine_days, routine_day_details\n"
                "✅ trainings, training_clients, muscle_groups, muscle_group_clients\n"
                "✅ events, event_users, type_events\n"
                "✅ notes, note_users, template_notes\n"
                "✅ progress_day_users, client_targets\n"
                "✅ user_parents"
            ),
        },
        {
            "name": "Sprint 6 - Routers secundarios",
            "desc": (
                "✅ aliments: UUID como id, filtro parent_id, created/updated_user_id\n"
                "✅ group_food / type_food: campo state renombrado a status\n"
                "✅ roles: generacion automatica de slug al crear\n"
                "✅ Todos los CRUDs: aliments, recipes, diets, routines, trainings, events, notes, progress"
            ),
        },
        {
            "name": "Sprint 7 - Eventos, Notas, Progreso",
            "desc": (
                "✅ Events / TypeEvents: CRUD completo\n"
                "✅ Notes / TemplateNotes: CRUD completo\n"
                "✅ ProgressDay / ClientTargets: CRUD completo\n"
                "✅ Modelos, schemas y routers consistentes con FK correctas"
            ),
        },
        {
            "name": "Sprint 8 - Recetas y fixes",
            "desc": (
                "✅ RecipeDetail.aliment_id: int -> str (UUID)\n"
                "✅ GET /recipes/client/{client_id}: corregido con UserDetail\n"
                "✅ Seed admin_user reescrito: crea User + UserDetail + RoleUser\n"
                "✅ ADMIN_EMAIL leido desde variable de entorno Railway"
            ),
        },
        {
            "name": "Sprint 9 - Roles, Estados y Módulo Forms",
            "desc": (
                "✅ 6 roles: superadmin, admin, setter, closer, coach, cliente\n"
                "✅ 15 estados de cliente (IDs 45-59): Pago pendiente → Cancelado/Reembolsado\n"
                "✅ Estado de cuenta: Activo / Inactivo\n"
                "✅ Módulo Forms completo:\n"
                "   - FormTemplate / FormTemplateField\n"
                "   - FormAssignment (UUID) / FormResponse\n"
                "   - 11 endpoints: CRUD plantillas + asignar + enviar + respuestas\n"
                "   - Auto-sync respuestas → perfil del cliente (peso, altura, etc.)\n"
                "   - Seed: Formulario de Bienvenida con 10 campos\n"
                "✅ Migración a1b2c3d4e5f6 con 4 tablas nuevas (total 37)\n"
                "✅ CI actualizado: assert >= 33 tablas, >= 50 rutas (121 activas)"
            ),
        },
    ],

    # ─────────────────────────────────────────────────────────────────────────
    # EN PROCESO
    # ─────────────────────────────────────────────────────────────────────────
    "En Proceso": [],

    # ─────────────────────────────────────────────────────────────────────────
    # POR HACER
    # ─────────────────────────────────────────────────────────────────────────
    "Por Hacer": [
        {
            "name": "Sprint 10 - QA Integral Forms",
            "desc": (
                "[ ] Login admin y obtener token JWT\n"
                "[ ] GET /api/form-templates/default → devuelve Formulario de Bienvenida\n"
                "[ ] POST /api/users → crear cliente de prueba\n"
                "[ ] POST /api/form-assignments → asignar formulario al cliente\n"
                "[ ] POST /api/form-assignments/{id}/submit → enviar respuestas\n"
                "[ ] GET /api/users/{id} → verificar que peso/altura se actualizaron\n"
                "[ ] Verificar status_id cliente: 48 (pendiente) → 49 (recibido)\n"
                "[ ] GET /api/parameters → confirmar los 15 estados de cliente"
            ),
        },
        {
            "name": "Sprint 11 - Dashboard Kanban de clientes",
            "desc": (
                "[ ] Endpoint GET /api/clients/kanban → clientes agrupados por estado\n"
                "[ ] Endpoint PATCH /api/clients/{id}/status → mover cliente de estado\n"
                "[ ] Filtros: por coach, por estado, por fecha\n"
                "[ ] Respuesta incluye datos básicos: nombre, email, estado, fecha ingreso"
            ),
        },
        {
            "name": "Sprint 12 - Check-ins semanales",
            "desc": (
                "[ ] Modelo WeeklyCheckin: cliente, fecha, peso, fotos, notas\n"
                "[ ] POST /api/checkins → crear check-in del cliente\n"
                "[ ] GET /api/checkins/client/{id} → historial del cliente\n"
                "[ ] Comparar peso actual vs objetivo vs semana anterior\n"
                "[ ] Notificación al coach cuando cliente envía check-in"
            ),
        },
        {
            "name": "Sprint 13 - Entrega del plan al cliente",
            "desc": (
                "[ ] Endpoint POST /api/plans/deliver → enviar plan por email al cliente\n"
                "[ ] Template de email con rutina + dieta asignada\n"
                "[ ] Estado cliente cambia a 'Plan entregado' (ID 54)\n"
                "[ ] PDF adjunto de la dieta (opcional, ver Sprint 16)"
            ),
        },
    ],

    # ─────────────────────────────────────────────────────────────────────────
    # BACKLOG
    # ─────────────────────────────────────────────────────────────────────────
    "Backlog": [
        {
            "name": "Sprint 14 - Analíticas y métricas",
            "desc": (
                "[ ] GET /api/analytics/overview → totales: clientes, activos, ingresos\n"
                "[ ] GET /api/analytics/clients → nuevos por semana/mes\n"
                "[ ] GET /api/analytics/states → distribución por estado kanban\n"
                "[ ] GET /api/analytics/checkins → adherencia y progreso promedio\n"
                "[ ] Filtros por rango de fechas y por coach"
            ),
        },
        {
            "name": "Sprint 15 - Upload de imágenes",
            "desc": (
                "[ ] Configurar AWS S3 o Cloudflare R2\n"
                "[ ] POST /api/files/upload → subir imagen, devolver URL\n"
                "[ ] Integrar en perfil de usuario (foto de perfil)\n"
                "[ ] Integrar en check-ins (fotos de progreso)\n"
                "[ ] Integrar en alimentos (foto del alimento)"
            ),
        },
        {
            "name": "Sprint 16 - PDF de dietas y rutinas",
            "desc": (
                "[ ] Implementar generación PDF en GET /api/diets/{id}/pdf\n"
                "[ ] Template HTML con macros, alimentos por comida, calorías\n"
                "[ ] PDF de rutina con ejercicios, series, repeticiones\n"
                "[ ] Descarga directa o link firmado S3"
            ),
        },
        {
            "name": "Sprint 17 - Frontend integration",
            "desc": (
                "[ ] Conectar frontend (Next.js / React) con API en Railway\n"
                "[ ] Configurar CORS para dominio del frontend\n"
                "[ ] Autenticación: guardar JWT en httpOnly cookie o localStorage\n"
                "[ ] Probar flujo completo: login → dashboard → kanban → form → check-in"
            ),
        },
        {
            "name": "Sprint 18 - Roles y permisos granulares",
            "desc": (
                "[ ] Middleware de autorización por rol (setter, closer, coach, admin)\n"
                "[ ] Setter: solo puede crear leads / asignar formularios\n"
                "[ ] Closer: puede ver y actualizar estados de pago\n"
                "[ ] Coach: solo ve sus clientes asignados\n"
                "[ ] Admin: acceso total excepto superadmin"
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
    rb = requests.get(f"{BASE}/boards/{BOARD_ID}", params=AUTH)
    if rb.status_code != 200:
        print(f"ERROR al conectar con el board: {rb.status_code} - {rb.text}")
        return
    board_real_id = rb.json()["id"]
    print(f"Board: {rb.json()['name']} ({board_real_id})")

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
        if not cards:
            continue
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
