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

# =============================================================================
# ESTADO ACTUAL DEL PROYECTO — actualizado 2026-05-25
#
# FASE 1 BACKEND: 100% completada
#   38 tablas en MySQL (Railway) · 128 rutas registradas
#   Módulos: auth, users, roles, params, países, menús,
#            alimentos, recetas, dietas, rutinas, entrenamientos,
#            eventos, notas, progreso, formularios, check-ins, planes
#
# FASE 2 EN CURSO:
#   ✅ Sprint 14 — Analíticas y métricas (4 endpoints)
#   ✅ Sprint 15 — Upload de imágenes (Cloudflare R2, boto3)
#   🔜 Sprint 16 — PDF de dietas y rutinas
#   🔜 Sprint 17 — Frontend completo
#   🔜 Sprint 18 — Roles y permisos granulares
#   🔜 Sprint 19 — Notificaciones internas
# =============================================================================

SPRINTS = {
    # ─────────────────────────────────────────────────────────────────────────
    # HECHO ✅
    # ─────────────────────────────────────────────────────────────────────────
    "Hecho": [
        {
            "name": "FASE 0 — Infraestructura base ✅",
            "desc": (
                "✅ FastAPI + SQLAlchemy 2 + Alembic sobre MySQL en Railway\n"
                "✅ Seeds idempotentes: 6 roles, 15 estados de cliente, países, menús, admin\n"
                "✅ JWT auth: login / refresh / logout / /me\n"
                "✅ Recuperar contraseña via Resend SDK (email real)\n"
                "✅ HTTPBearer en Swagger UI\n"
                "✅ Deploy continuo en Railway (.up.railway.app)\n"
                "✅ CI/CD GitHub Actions: lint + validación de modelos + validación de rutas\n"
                "✅ CORS abierto listo para conectar frontend"
            ),
        },
        {
            "name": "Sprint 1-8 — Modelos, migraciones y CRUDs ✅",
            "desc": (
                "✅ 33 tablas base migradas\n"
                "✅ users / user_details / roles / parameters / countries / menus\n"
                "✅ aliments (UUID) / aliment_descriptions / type_foods / group_foods\n"
                "✅ recipes / recipe_details\n"
                "✅ diets / diet_details / diet_foods / diet_food_aliments\n"
                "✅ routines / routine_days / routine_day_details\n"
                "✅ trainings / training_clients / muscle_groups / muscle_group_clients\n"
                "✅ events / event_users / type_events\n"
                "✅ notes / note_users / template_notes\n"
                "✅ progress_day_users / client_targets / user_parents\n"
                "✅ CRUDs completos para todos los módulos anteriores"
            ),
        },
        {
            "name": "Sprint 9 — Roles, estados y módulo Forms ✅",
            "desc": (
                "✅ 6 roles: superadmin, admin, setter, closer, coach, cliente\n"
                "✅ 15 estados del flujo de cliente: Pago pendiente → Cancelado\n"
                "✅ Formularios de intake:\n"
                "   · FormTemplate + FormTemplateField (plantillas personalizables)\n"
                "   · FormAssignment (asignación UUID por cliente)\n"
                "   · FormResponse (respuestas guardadas en BD)\n"
                "   · Auto-sync respuestas → perfil del cliente (peso, altura, etc.)\n"
                "   · Seed: Formulario de Bienvenida con 10 campos\n"
                "✅ 11 endpoints: CRUD plantillas + asignar + enviar + ver respuestas\n"
                "✅ Estado cliente: Formulario pendiente → Formulario recibido (automático)"
            ),
        },
        {
            "name": "Sprint 10 — QA integral formularios ✅",
            "desc": (
                "✅ Script qa_forms.py con 16 checks automatizados contra Railway\n"
                "✅ Flujo completo verificado en producción:\n"
                "   login → crear cliente → asignar form → submit → perfil actualizado\n"
                "✅ Protecciones validadas: doble asignación y doble submit bloqueados\n"
                "✅ 7 respuestas guardadas correctamente en BD\n"
                "✅ IDs de estado resueltos dinámicamente (sin hardcoding)"
            ),
        },
        {
            "name": "Sprint 11 — Dashboard Kanban ✅",
            "desc": (
                "✅ GET /api/users/kanban → clientes agrupados por estado con nombre\n"
                "✅ Filtro ?coach_id=UUID → solo clientes del coach\n"
                "✅ PUT /api/users/{id}/change → cambio de estado (drag & drop)\n"
                "✅ Verificado en producción: 3 clientes en 2 columnas"
            ),
        },
        {
            "name": "Sprint 12 — Check-ins semanales ✅",
            "desc": (
                "✅ Tabla weekly_checkins (UUID, cliente, coach, fecha, peso, notas)\n"
                "✅ POST /api/checkins → registrar check-in del cliente\n"
                "✅ GET /api/checkins/client/{id} → historial + delta de peso semana a semana\n"
                "✅ GET /api/checkins/summary/{id} → cambio total de peso desde inicio\n"
                "✅ PUT /api/checkins/{id}/coach-notes → feedback del coach\n"
                "✅ DELETE /api/checkins/{id} → eliminar registro"
            ),
        },
        {
            "name": "Sprint 13 — Entrega del plan por email ✅",
            "desc": (
                "✅ POST /api/plans/deliver → envía email HTML al cliente\n"
                "✅ Email incluye: macros (kcal/proteínas/carbos/grasas), días de rutina\n"
                "   y mensaje personalizado del coach\n"
                "✅ Estado cliente → 'Plan entregado' de forma automática\n"
                "✅ Dieta y rutina son opcionales (se puede enviar solo mensaje)\n"
                "✅ Verificado en producción con email real (Resend SDK)"
            ),
        },
        {
            "name": "Sprint 14 — Analíticas y métricas ✅",
            "desc": (
                "✅ GET /api/analytics/overview\n"
                "   → total clientes, activos, nuevos este mes, coaches, total check-ins\n"
                "✅ GET /api/analytics/states\n"
                "   → distribución de clientes por estado con porcentajes\n"
                "✅ GET /api/analytics/checkins\n"
                "   → adherencia (%), cambio de peso promedio, tendencia semanal (8 semanas)\n"
                "✅ GET /api/analytics/coaches\n"
                "   → clientes asignados y check-ins recibidos por coach\n"
                "✅ Filtros: ?coach_id=uuid en todos los endpoints\n"
                "✅ Frontend analytics.html: 6 tarjetas + gráfico barras + dona + línea + tabla coaches\n"
                "✅ Gráficos SVG sin librerías externas"
            ),
        },
        {
            "name": "Sprint 15 — Upload de imágenes ✅",
            "desc": (
                "✅ Cloudflare R2 configurado (S3-compatible con boto3)\n"
                "✅ POST /api/files/upload → sube imagen, devuelve URL pública\n"
                "✅ DELETE /api/files/delete → elimina archivo por key\n"
                "✅ GET /api/files/list → lista archivos por carpeta\n"
                "✅ Límite: 10 MB · Formatos: JPG, PNG, WEBP, GIF\n"
                "✅ Carpetas: uploads, profiles, checkins, aliments\n"
                "✅ Integrado en client-profile.html: avatar con hover overlay + click para subir\n"
                "✅ Integrado en checkins.html: foto de progreso con preview + lightbox\n"
                "✅ URL pública activa: pub-397ed3b6f1d1480d8c17d960513a3c78.r2.dev\n"
                "✅ Verificado en producción: upload retorna 200 con URL pública real"
            ),
        },
    ],

    # ─────────────────────────────────────────────────────────────────────────
    # EN PROCESO
    # ─────────────────────────────────────────────────────────────────────────
    "En Proceso": [],

    # ─────────────────────────────────────────────────────────────────────────
    # POR HACER — FASE 2
    # ─────────────────────────────────────────────────────────────────────────
    "Por Hacer": [
        {
            "name": "Sprint 16 — PDF de dietas y rutinas",
            "desc": (
                "[ ] GET /api/diets/{id}/pdf → PDF con macros y alimentos por comida\n"
                "[ ] GET /api/routines/{id}/pdf → PDF con días, ejercicios, series/reps\n"
                "[ ] Template HTML → PDF con WeasyPrint o similar\n"
                "[ ] Adjuntar PDF al email de entrega del plan (Sprint 13)"
            ),
        },
    ],

    # ─────────────────────────────────────────────────────────────────────────
    # BACKLOG — FASE 3
    # ─────────────────────────────────────────────────────────────────────────
    "Backlog": [
        {
            "name": "Sprint 17 — Frontend avanzado y pulido",
            "desc": (
                "[ ] Notificaciones in-app (badge de pendientes)\n"
                "[ ] Modo oscuro / tema personalizable\n"
                "[ ] Paginación infinita en listados grandes\n"
                "[ ] Vista móvil / PWA (manifest.json + service worker)\n"
                "[ ] Exportar tabla de clientes a CSV\n"
                "[ ] Filtros avanzados en kanban y check-ins"
            ),
        },
        {
            "name": "Sprint 18 — Roles y permisos granulares",
            "desc": (
                "[ ] Middleware de autorización por rol en cada endpoint\n"
                "[ ] Setter: crear leads, asignar formularios\n"
                "[ ] Closer: ver y actualizar estados de pago\n"
                "[ ] Coach: solo sus clientes asignados, sin acceso admin\n"
                "[ ] Admin: acceso total excepto panel superadmin\n"
                "[ ] Superadmin: gestión de cuentas y configuración global"
            ),
        },
        {
            "name": "Sprint 19 — Notificaciones internas",
            "desc": (
                "[ ] Notificar al coach cuando cliente envía formulario\n"
                "[ ] Notificar al coach cuando cliente sube check-in\n"
                "[ ] Notificar al cliente cuando el coach deja notas\n"
                "[ ] Canal: email (Resend) y/o webhook configurable"
            ),
        },
    ],
}


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
