"""
Sincroniza el estado del proyecto con el board de Trello.
- Mueve cards existentes a la lista correcta si ya existen
- Crea cards nuevas si no existen
- No duplica

Uso:
  pip install requests
  export TRELLO_API_KEY="..."
  export TRELLO_TOKEN="..."
  export TRELLO_BOARD_ID="..."
  python scripts/setup_trello.py
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
    print("PowerShell:")
    print('  $env:TRELLO_API_KEY="tu_api_key"')
    print('  $env:TRELLO_TOKEN="tu_token"')
    print('  $env:TRELLO_BOARD_ID="tu_board_id"')
    print()
    print("Bash / Railway shell:")
    print('  export TRELLO_API_KEY="tu_api_key"')
    print('  export TRELLO_TOKEN="tu_token"')
    print('  export TRELLO_BOARD_ID="tu_board_id"')
    sys.exit(1)

AUTH  = {"key": API_KEY, "token": TOKEN}
LISTAS = ["Backlog", "Por Hacer", "En Proceso", "Control de Calidad", "Hecho"]

# =============================================================================
# ESTADO DEL PROYECTO — actualizado 2026-05-28
#
# FASE 0 + FASE 1 BACKEND: ✅ 100%
# FASE 2 FRONTEND + UX:    ✅ 100%  (Sprints 14–19 + extras)
# FASE 3 NUTRICIÓN:        🔄 En proceso (Días 9–13)
# =============================================================================

SPRINTS = {

    # ──────────────────────────────────────────────────────────────────────────
    # HECHO ✅
    # ──────────────────────────────────────────────────────────────────────────
    "Hecho": [
        {
            "name": "FASE 0 — Infraestructura base ✅",
            "desc": (
                "✅ FastAPI + SQLAlchemy 2 + Alembic sobre MySQL en Railway\n"
                "✅ Seeds idempotentes: 6 roles, 15 estados de cliente, países, menús, admin\n"
                "✅ JWT auth: login / refresh / logout / /me\n"
                "✅ Recuperar contraseña via Resend SDK (email real)\n"
                "✅ HTTPBearer en Swagger UI\n"
                "✅ Deploy continuo en Railway (nutrientrena-production.up.railway.app)\n"
                "✅ CI/CD GitHub Actions: lint + validación de modelos y rutas\n"
                "✅ CORS abierto listo para conectar frontend"
            ),
        },
        {
            "name": "Sprints 1–8 — Modelos, migraciones y CRUDs ✅",
            "desc": (
                "✅ 38 tablas en MySQL, 128+ rutas registradas\n"
                "✅ users / user_details / roles / parameters / countries / menus\n"
                "✅ aliments / type_foods / group_foods / recipes\n"
                "✅ diets / diet_details / diet_foods / diet_food_aliments\n"
                "✅ routines / routine_days / routine_day_details\n"
                "✅ trainings / muscle_groups / events / notes\n"
                "✅ progress_day_users / client_targets / user_parents\n"
                "✅ weekly_checkins / plan_deliveries\n"
                "✅ form_templates / form_assignments / form_responses\n"
                "✅ CRUDs completos para todos los módulos"
            ),
        },
        {
            "name": "Sprint 9 — Roles, estados y módulo Forms ✅",
            "desc": (
                "✅ 6 roles: superadmin, admin, setter, closer, coach, cliente\n"
                "✅ 15 estados del flujo de cliente (Pago pendiente → Cancelado)\n"
                "✅ Formularios de intake con plantillas personalizables (18+ campos)\n"
                "✅ FormAssignment por cliente (UUID)\n"
                "✅ FormResponse: auto-sync respuestas → perfil del cliente\n"
                "✅ 11 endpoints: CRUD plantillas + asignar + enviar + ver respuestas\n"
                "✅ Estado automático: Formulario pendiente → Formulario recibido"
            ),
        },
        {
            "name": "Sprint 10 — QA integral formularios ✅",
            "desc": (
                "✅ Script qa_forms.py con 16 checks automatizados contra Railway\n"
                "✅ Flujo completo verificado en producción\n"
                "✅ Protecciones: doble asignación y doble submit bloqueados\n"
                "✅ IDs de estado resueltos dinámicamente"
            ),
        },
        {
            "name": "Sprint 11 — Dashboard Kanban ✅",
            "desc": (
                "✅ GET /api/users/kanban → clientes agrupados por estado\n"
                "✅ Filtro ?coach_id=UUID → solo clientes del coach\n"
                "✅ PUT /api/users/{id}/change → cambio de estado (drag & drop)\n"
                "✅ Frontend kanban.html con columnas arrastrables"
            ),
        },
        {
            "name": "Sprint 12 — Check-ins semanales ✅",
            "desc": (
                "✅ Tabla weekly_checkins (UUID, cliente, coach, fecha, peso, notas)\n"
                "✅ POST /api/checkins → registrar check-in\n"
                "✅ GET /api/checkins/client/{id} → historial + delta de peso\n"
                "✅ GET /api/checkins/summary/{id} → cambio total desde inicio\n"
                "✅ PUT /api/checkins/{id}/coach-notes → feedback del coach\n"
                "✅ DELETE /api/checkins/{id}"
            ),
        },
        {
            "name": "Sprint 13 — Entrega del plan por email ✅",
            "desc": (
                "✅ POST /api/plans/deliver → email HTML al cliente\n"
                "✅ Email con macros (kcal/proteínas/carbs/grasas) + días de rutina\n"
                "✅ Mensaje personalizado del coach + enlace Loom\n"
                "✅ Estado cliente → 'Plan entregado' automático\n"
                "✅ Verificado en producción con Resend SDK"
            ),
        },
        {
            "name": "Sprint 14 — Analíticas y métricas ✅",
            "desc": (
                "✅ GET /api/analytics/overview → clientes, check-ins, coaches\n"
                "✅ GET /api/analytics/states → distribución por estado (%)\n"
                "✅ GET /api/analytics/checkins → adherencia, cambio de peso, tendencia 8 semanas\n"
                "✅ GET /api/analytics/coaches → clientes y check-ins por coach\n"
                "✅ Frontend analytics.html: gráficos SVG sin librerías externas"
            ),
        },
        {
            "name": "Sprint 15 — Upload de imágenes (Cloudflare R2) ✅",
            "desc": (
                "✅ Cloudflare R2 configurado (S3-compatible, boto3)\n"
                "✅ POST /api/files/upload → URL pública\n"
                "✅ Límite 10 MB · Formatos: JPG, PNG, WEBP, GIF\n"
                "✅ Avatar de cliente editable con hover overlay\n"
                "✅ Foto de progreso en check-ins con preview + lightbox"
            ),
        },
        {
            "name": "Sprint 16 — Generación de PDF ✅",
            "desc": (
                "✅ GET /api/diets/{id}/pdf → PDF con macros y alimentos por comida\n"
                "✅ GET /api/routines/{id}/pdf → PDF con días, ejercicios y descripción\n"
                "✅ Descarga directa desde diets.html y routines.html\n"
                "✅ Clon de dietas y rutinas (POST /diets/clone, POST /routines/clone)"
            ),
        },
        {
            "name": "Sprint 17 — Frontend avanzado ✅",
            "desc": (
                "✅ Exportación CSV de clientes\n"
                "✅ Filtros por estado, coach, país en clients.html\n"
                "✅ Badges de estado con colores semánticos\n"
                "✅ diets.html: tarjetas con macros, foods tags, PDF, clon, eliminar\n"
                "✅ routines.html: tarjetas con chips, editor por días, PDF, clon\n"
                "✅ Diseño responsivo en todas las páginas"
            ),
        },
        {
            "name": "Sprint 18 — Control de acceso por roles ✅",
            "desc": (
                "✅ require_role_ids() en todos los endpoints\n"
                "✅ verify_client_access() → coaches solo ven sus clientes\n"
                "✅ Roles: Superadmin, Admin, Setter, Closer, Coach, Cliente\n"
                "✅ Setter/Closer acceden a catálogos; Coach accede a sus clientes"
            ),
        },
        {
            "name": "Sprint 19 — Notificaciones por email ✅",
            "desc": (
                "✅ Email al coach cuando cliente registra check-in\n"
                "✅ Email al cliente cuando coach deja notas\n"
                "✅ Email con link al formulario de intake al asignarlo\n"
                "✅ Email con resumen de plan (dieta + rutina + Loom)\n"
                "✅ Todas las plantillas con branding NutriEntrena (purple #5B2D8E)"
            ),
        },
        {
            "name": "Extras Fase 2 — CRM + perfil extendido ✅",
            "desc": (
                "✅ Campos CRM en user_details: plan_comprado, precio, estado_pago,\n"
                "   importe_pagado/pendiente, fecha_compra, fecha_limite_entrega,\n"
                "   responsable_venta, crm_origen, whatsapp_link, consentimiento\n"
                "✅ Migración c3d4e5f6a7b8 aplicada en Railway\n"
                "✅ Tab Comercial en client-profile.html con grid editable\n"
                "✅ GET /api/plans/history/{client_id} → historial de entregas\n"
                "✅ POST /api/plans/resend/{id} → reenviar email de entrega"
            ),
        },
        {
            "name": "Fase 3 / Sprint 20 — Portal público para clientes ✅",
            "desc": (
                "✅ GET /api/public/form/{assignment_id} → sin autenticación\n"
                "✅ POST /api/public/form/{assignment_id}/submit\n"
                "✅ Página public/form.html: formulario dinámico con barra de progreso\n"
                "✅ Estados: cargando → formulario → enviado / ya respondido / error\n"
                "✅ FRONTEND_URL env var en Railway controla el link del formulario"
            ),
        },
        {
            "name": "Fase 3 / Sprint 21 — Perfil de cliente extendido ✅",
            "desc": (
                "✅ 4 tabs en client-profile.html: Resumen | Formulario | Entregas | Comercial\n"
                "✅ Resumen: stats (check-ins, peso, estado), gráfica SVG de evolución\n"
                "✅ Formulario: 3 estados (sin asignar / pendiente / respondido con labels)\n"
                "✅ Entregas: historial con chips de dieta/rutina/email/Loom\n"
                "✅ Botón Re-enviar email en cada entrega previa\n"
                "✅ Badge de formulario pendiente en tab"
            ),
        },
        {
            "name": "Fase 3 / Sprint 22 — Check-ins con mediciones corporales ✅",
            "desc": (
                "✅ 7 nuevas columnas: body_fat, waist, chest, hips, arms, legs, photo_url\n"
                "✅ Migración Alembic e5f6a7b8c9d0 aplicada en Railway\n"
                "✅ Modal de nuevo check-in: sección de mediciones en grid 3 columnas\n"
                "✅ Modal de notas del coach: edita mediciones + peso\n"
                "✅ Tabla con resumen de mediciones por check-in"
            ),
        },
        {
            "name": "Fase 3 / Sprint 23 — UX entregas de planes ✅",
            "desc": (
                "✅ Historial muestra nombre real de dieta y rutina (antes solo ID)\n"
                "✅ Botón Re-enviar email en cada entrega del historial\n"
                "✅ POST /api/plans/resend/{delivery_id}\n"
                "✅ Preview inline de macros al seleccionar dieta en modal\n"
                "✅ Helpers _build_diet_payload / _build_routine_payload reutilizables"
            ),
        },
        {
            "name": "Fase 3 / Día 9 — Catálogos de nutrición ✅",
            "desc": (
                "✅ nutrition-catalog.html: dos paneles (Tipos de alimento | Grupos de alimento)\n"
                "✅ CRUD completo: crear, editar, eliminar (soft-delete via PUT status=0)\n"
                "✅ Búsqueda en tiempo real + contador + atajos de teclado\n"
                "✅ Fix bug schema food.py: state → status (el CRUD no funcionaba antes)\n"
                "✅ Sidebar con sección Nutrición: Catálogos → Alimentos → Recetas → Dietas"
            ),
        },
    ],

    # ──────────────────────────────────────────────────────────────────────────
    # EN PROCESO
    # ──────────────────────────────────────────────────────────────────────────
    "En Proceso": [
        {
            "name": "Fase 3 — Nutrición frontend 🔄",
            "desc": (
                "✅ Día 9: nutrition-catalog.html (Tipos + Grupos)\n"
                "🔄 Día 10: aliments.html — CRUD + importación masiva CSV\n"
                "[ ] Día 11: recipes.html — CRUD + asignación a cliente\n"
                "[ ] Día 12: diets.html — ya entregado ✅\n"
                "[ ] Día 13: Metas del cliente — peso objetivo vs actual en perfil"
            ),
        },
    ],

    # ──────────────────────────────────────────────────────────────────────────
    # POR HACER — Fase 3 pendiente
    # ──────────────────────────────────────────────────────────────────────────
    "Por Hacer": [
        {
            "name": "Fase 3 / Día 10 — aliments.html",
            "desc": (
                "[ ] Tabla de alimentos con búsqueda + paginación\n"
                "[ ] Modal crear/editar: nombre, grupo, macros (prot/carbs/grasas/kcal)\n"
                "[ ] Importación masiva desde CSV (POST /api/aliments/import)\n"
                "[ ] Preview de CSV antes de importar\n"
                "[ ] Backend: GET /api/aliments/search con filtros"
            ),
        },
        {
            "name": "Fase 3 / Día 11 — recipes.html",
            "desc": (
                "[ ] Listado de recetas con búsqueda\n"
                "[ ] Modal crear/editar: nombre, ingredientes, instrucciones\n"
                "[ ] Asignar receta a cliente (POST /api/recipes/assign)\n"
                "[ ] Ver recetas asignadas por cliente"
            ),
        },
        {
            "name": "Fase 3 / Día 13 — Metas del cliente",
            "desc": (
                "[ ] Tab o sección 'Metas' en client-profile.html\n"
                "[ ] Registrar peso objetivo (ClientTarget)\n"
                "[ ] Gráfica peso actual vs peso objetivo a lo largo del tiempo\n"
                "[ ] Indicador de progreso porcentual hacia la meta\n"
                "[ ] Backend: POST /api/client-targets, GET /api/client-targets/search"
            ),
        },
    ],

    # ──────────────────────────────────────────────────────────────────────────
    # BACKLOG — ideas futuras
    # ──────────────────────────────────────────────────────────────────────────
    "Backlog": [
        {
            "name": "Log de entrenamiento estilo Hevy",
            "desc": (
                "[ ] Registrar sesiones de entrenamiento: ejercicio, series, reps, carga\n"
                "[ ] Historial por cliente y por ejercicio\n"
                "[ ] Progresión de fuerza en gráfica"
            ),
        },
        {
            "name": "Dashboard enriquecido",
            "desc": (
                "[ ] Métricas reales: clientes activos, check-ins recientes\n"
                "[ ] Pipeline CRM en el dashboard\n"
                "[ ] Alertas: clientes sin check-in en 2+ semanas\n"
                "[ ] Clientes con fecha límite de entrega próxima"
            ),
        },
        {
            "name": "Vista móvil / PWA",
            "desc": (
                "[ ] manifest.json + service worker\n"
                "[ ] Navegación responsiva en móvil\n"
                "[ ] Notificaciones push"
            ),
        },
    ],
}


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def get_all_cards(board_real_id: str) -> dict:
    """Devuelve {nombre_normalizado: card_dict} de todas las cards del board."""
    r = requests.get(
        f"{BASE}/boards/{board_real_id}/cards",
        params={**AUTH, "fields": "id,name,idList"},
    )
    if r.status_code != 200:
        print(f"ERROR al obtener cards: {r.status_code}")
        return {}
    return {c["name"].strip(): c for c in r.json()}


def upsert_card(nombre: str, desc: str, lista_id: str, existing_cards: dict):
    card = existing_cards.get(nombre.strip())
    if card:
        if card["idList"] != lista_id:
            requests.put(
                f"{BASE}/cards/{card['id']}",
                params={**AUTH, "idList": lista_id, "desc": desc},
            )
            print(f"      → Movida a lista correcta")
        else:
            requests.put(
                f"{BASE}/cards/{card['id']}",
                params={**AUTH, "desc": desc},
            )
            print(f"      → Descripción actualizada")
    else:
        r = requests.post(
            f"{BASE}/cards",
            params={**AUTH, "name": nombre, "desc": desc, "idList": lista_id},
        )
        if r.status_code != 200:
            print(f"      ERROR al crear card: {r.status_code} - {r.text}")
        else:
            print(f"      → Creada")


def main():
    rb = requests.get(f"{BASE}/boards/{BOARD_ID}", params=AUTH)
    if rb.status_code != 200:
        print(f"ERROR al conectar con el board: {rb.status_code} - {rb.text}")
        return
    board_real_id = rb.json()["id"]
    print(f"Board: {rb.json()['name']} ({board_real_id})\n")

    # Obtener / crear listas
    r = requests.get(f"{BASE}/boards/{board_real_id}/lists", params=AUTH)
    existentes = r.json()
    lista_ids = {l["name"]: l["id"] for l in existentes}

    for nombre in LISTAS:
        if nombre not in lista_ids:
            print(f"Creando lista: {nombre}")
            rr = requests.post(
                f"{BASE}/lists",
                params={**AUTH, "name": nombre, "idBoard": board_real_id},
            )
            if rr.status_code == 200:
                lista_ids[nombre] = rr.json()["id"]
            else:
                print(f"  ERROR: {rr.status_code}")
        else:
            print(f"Lista OK: {nombre}")

    print()

    # Obtener todas las cards existentes para no duplicar
    existing_cards = get_all_cards(board_real_id)
    print(f"Cards existentes en el board: {len(existing_cards)}\n")

    # Upsert cards
    print("Sincronizando cards…")
    for lista_nombre, cards in SPRINTS.items():
        if not cards or lista_nombre not in lista_ids:
            continue
        lista_id = lista_ids[lista_nombre]
        for card in cards:
            print(f"  [{lista_nombre}] {card['name']}")
            upsert_card(card["name"], card["desc"], lista_id, existing_cards)

    print(f"\n✅ Listo: https://trello.com/b/{BOARD_ID}")


if __name__ == "__main__":
    main()
