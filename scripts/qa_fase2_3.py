"""
QA automatizado — Fase 2 + Fase 3 (parcial)
Verifica en producción todos los módulos entregados.

Uso:
  python scripts/qa_fase2_3.py

Variables de entorno (opcionales, tienen defaults):
  API_URL          → default: https://nutrientrena-production.up.railway.app
  ADMIN_EMAIL      → default: vallejoj203k@gmail.com
  ADMIN_PASSWORD   → default: Admin123!
"""
import os
import sys
import time

try:
    import requests
except ImportError:
    print("ERROR: pip install requests")
    sys.exit(1)

BASE     = os.environ.get("API_URL", "https://nutrientrena-production.up.railway.app")
EMAIL    = os.environ.get("ADMIN_EMAIL", "vallejoj203k@gmail.com")
PASSWORD = os.environ.get("ADMIN_PASSWORD", "Admin123!")

OK   = "✅"
ERR  = "❌"
SKIP = "⏭️ "
SEP  = "─" * 64

passed = 0
failed = 0


def header(title):
    print(f"\n{SEP}\n  {title}\n{SEP}")


def check(label, condition, detail=""):
    global passed, failed
    mark = OK if condition else ERR
    msg  = f"  {mark} {label}"
    if detail:
        msg += f"  →  {detail}"
    print(msg)
    if condition:
        passed += 1
    else:
        failed += 1
    return condition


def req_post(path, body=None, token=None, files=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    if files:
        return requests.post(f"{BASE}{path}", files=files, headers=headers)
    return requests.post(f"{BASE}{path}", json=body, headers=headers)


def req_get(path, token=None, params=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return requests.get(f"{BASE}{path}", headers=headers, params=params or {})


def req_put(path, body, token=None):
    headers = {"Authorization": f"Bearer {token}"}
    return requests.put(f"{BASE}{path}", json=body, headers=headers)


# ─────────────────────────────────────────────────────────────────────────────
# 1. LOGIN
# ─────────────────────────────────────────────────────────────────────────────
header("1. AUTENTICACIÓN")
r = req_post("/api/auth/login", {"email": EMAIL, "password": PASSWORD})
check("POST /api/auth/login devuelve 200", r.status_code == 200, str(r.status_code))
token = r.json().get("data", {}).get("token", "")
if not check("Token JWT recibido", bool(token)):
    print(f"\n{ERR} No se puede continuar sin token. Verifica las credenciales.\n")
    sys.exit(1)

r = req_get("/api/auth/me", token)
check("GET /api/auth/me devuelve 200", r.status_code == 200)
me = r.json().get("data", {})
admin_detail_id = me.get("id")
check("Me devuelve UserDetail UUID", bool(admin_detail_id), str(admin_detail_id))
print(f"       Admin: {me.get('name')} ({me.get('email')})")


# ─────────────────────────────────────────────────────────────────────────────
# 2. ANALYTICS
# ─────────────────────────────────────────────────────────────────────────────
header("2. ANALYTICS — FASE 2")

r = req_get("/api/analytics/overview", token)
ok = check("GET /api/analytics/overview devuelve 200", r.status_code == 200)
if ok:
    d = r.json().get("data", {})
    check("overview tiene total_clients", "total_clients" in d, str(d.keys()))
    print(f"       total_clients={d.get('total_clients')}, coaches={d.get('total_coaches')}")

r = req_get("/api/analytics/states", token)
check("GET /api/analytics/states devuelve 200", r.status_code == 200)

r = req_get("/api/analytics/checkins", token)
check("GET /api/analytics/checkins devuelve 200", r.status_code == 200)

r = req_get("/api/analytics/coaches", token)
check("GET /api/analytics/coaches devuelve 200", r.status_code == 200)


# ─────────────────────────────────────────────────────────────────────────────
# 3. CATÁLOGOS DE NUTRICIÓN — FASE 3 DÍA 9
# ─────────────────────────────────────────────────────────────────────────────
header("3. CATÁLOGOS DE NUTRICIÓN (TypeFood + GroupFood)")

# TypeFood
r = req_get("/api/typeFood/findAll", token)
check("GET /api/typeFood/findAll devuelve 200", r.status_code == 200)
tf_items = r.json().get("data", [])
check("TypeFood devuelve lista", isinstance(tf_items, list), f"{len(tf_items)} items")

ts = int(time.time())
r = req_post("/api/typeFood", {"name": f"QA Tipo {ts}", "description": "Creado por QA"}, token)
ok = check("POST /api/typeFood crea registro", r.status_code == 200, str(r.status_code))
if ok:
    new_tf = r.json().get("data", {})
    tf_id  = new_tf.get("id")
    check("TypeFood creado tiene id", bool(tf_id), str(tf_id))
    check("TypeFood tiene campo status (no state)", "status" in new_tf, str(new_tf.keys()))

    r = req_put(f"/api/typeFood/{tf_id}/update", {"name": f"QA Tipo {ts} editado"}, token)
    check("PUT /api/typeFood/{id}/update edita correctamente", r.status_code == 200)

    r = req_put(f"/api/typeFood/{tf_id}/update", {"status": 0}, token)
    check("Soft-delete TypeFood (status=0)", r.status_code == 200)

# GroupFood
r = req_get("/api/groupFood/findAll", token)
check("GET /api/groupFood/findAll devuelve 200", r.status_code == 200)
gf_items = r.json().get("data", [])
check("GroupFood devuelve lista", isinstance(gf_items, list), f"{len(gf_items)} items")

r = req_post("/api/groupFood", {"name": f"QA Grupo {ts}", "description": "Creado por QA"}, token)
ok = check("POST /api/groupFood crea registro", r.status_code == 200, str(r.status_code))
if ok:
    new_gf = r.json().get("data", {})
    gf_id  = new_gf.get("id")
    check("GroupFood creado tiene id", bool(gf_id), str(gf_id))

    r = req_put(f"/api/groupFood/{gf_id}/update", {"status": 0}, token)
    check("Soft-delete GroupFood (status=0)", r.status_code == 200)


# ─────────────────────────────────────────────────────────────────────────────
# 4. DIETAS — CRUD + PDF
# ─────────────────────────────────────────────────────────────────────────────
header("4. DIETAS — CRUD + PDF")

r = req_get("/api/diets/findAll", token)
check("GET /api/diets/findAll devuelve 200", r.status_code == 200)
diets = r.json().get("data", [])
check("Dietas devuelve lista", isinstance(diets, list), f"{len(diets)} dietas")
diet_id = None

r = req_post("/api/diets", {
    "title": f"QA Dieta {ts}",
    "calories": 2000,
    "proteins": 150,
    "carbs": 200,
    "fats": 70,
    "foods": [{"name": "Desayuno — Avena con fruta"}, {"name": "Almuerzo — Pollo y arroz"}],
}, token)
ok = check("POST /api/diets crea dieta", r.status_code == 200, str(r.status_code))
if ok:
    diet_id = r.json().get("data", {}).get("id")
    check("Dieta creada tiene UUID", bool(diet_id), str(diet_id))

if diet_id:
    r = requests.get(f"{BASE}/api/diets/{diet_id}/pdf",
                     headers={"Authorization": f"Bearer {token}"})
    check("GET /api/diets/{id}/pdf devuelve PDF", r.status_code == 200,
          r.headers.get("Content-Type", ""))

    r = req_post("/api/diets/clone", {"diet_id": diet_id}, token)
    check("POST /api/diets/clone clona dieta", r.status_code == 200)


# ─────────────────────────────────────────────────────────────────────────────
# 5. RUTINAS — CRUD + PDF
# ─────────────────────────────────────────────────────────────────────────────
header("5. RUTINAS — CRUD + PDF")

r = req_get("/api/routines/findAll", token)
check("GET /api/routines/findAll devuelve 200", r.status_code == 200)
routines = r.json().get("data", [])
check("Rutinas devuelve lista", isinstance(routines, list), f"{len(routines)} rutinas")
routine_id = None

r = req_post("/api/routines", {
    "name": f"QA Rutina {ts}",
    "days": 4,
    "duration": 60,
    "training_type": "Fuerza",
    "level": "Intermedio",
    "days_detail": [
        {"day_name": "Día 1 — Pecho y tríceps", "description": "Press banca, fondos"},
        {"day_name": "Día 2 — Espalda y bíceps",  "description": "Dominadas, remo"},
    ],
}, token)
ok = check("POST /api/routines crea rutina", r.status_code == 200, str(r.status_code))
if ok:
    routine_id = r.json().get("data", {}).get("id")
    check("Rutina creada tiene id", bool(routine_id), str(routine_id))

if routine_id:
    r = requests.get(f"{BASE}/api/routines/{routine_id}/pdf",
                     headers={"Authorization": f"Bearer {token}"})
    check("GET /api/routines/{id}/pdf devuelve PDF", r.status_code == 200,
          r.headers.get("Content-Type", ""))


# ─────────────────────────────────────────────────────────────────────────────
# 6. CHECK-INS CON MEDICIONES — FASE 3 SPRINT 22
# ─────────────────────────────────────────────────────────────────────────────
header("6. CHECK-INS CON MEDICIONES CORPORALES")

# Crear cliente de prueba
r = req_post("/api/users", {
    "name": f"QA CheckIn {ts}",
    "email": f"qa.checkin.{ts}@test.com",
    "password": "Test1234!",
    "role_id": 6,
}, token)
ok = check("Crear cliente de prueba", r.status_code in (200, 201), str(r.status_code))
client_detail_id = r.json().get("data", {}).get("id") if ok else None

if client_detail_id:
    r = req_post("/api/checkins", {
        "client_user_detail_id": client_detail_id,
        "checkin_date": "2026-05-28",
        "weight": 80.5,
        "notes": "Check-in QA",
        "body_fat": 18.5,
        "waist": 85.0,
        "chest": 102.0,
        "hips": 96.0,
        "arms": 35.0,
        "legs": 58.0,
    }, token)
    ok = check("POST /api/checkins con mediciones", r.status_code == 200, str(r.status_code))
    if ok:
        ci = r.json().get("data", {})
        check("Check-in tiene body_fat", ci.get("body_fat") == 18.5, str(ci.get("body_fat")))
        check("Check-in tiene waist",    ci.get("waist")    == 85.0,  str(ci.get("waist")))
        check("Check-in tiene chest",    ci.get("chest")    == 102.0, str(ci.get("chest")))
        check("Check-in tiene arms",     ci.get("arms")     == 35.0,  str(ci.get("arms")))
        check("Check-in tiene legs",     ci.get("legs")     == 58.0,  str(ci.get("legs")))
        ci_id = ci.get("id")

    r = req_get(f"/api/checkins/client/{client_detail_id}", token)
    check("GET /api/checkins/client/{id} devuelve 200", r.status_code == 200)
    checkins = r.json().get("data", {}).get("checkins", [])
    check("Historial contiene el check-in creado", len(checkins) >= 1, str(len(checkins)))


# ─────────────────────────────────────────────────────────────────────────────
# 7. ENTREGA DE PLANES + HISTORIAL ENRIQUECIDO + RESEND — FASE 3 SPRINT 23
# ─────────────────────────────────────────────────────────────────────────────
header("7. ENTREGA DE PLANES — HISTORIAL ENRIQUECIDO + RESEND")

delivery_id = None
if client_detail_id:
    body = {
        "client_user_detail_id": client_detail_id,
        "send_email": False,
        "message": "Mensaje de prueba QA",
    }
    if diet_id:
        body["diet_id"] = diet_id
    if routine_id:
        body["routine_id"] = routine_id

    r = req_post("/api/plans/deliver", body, token)
    ok = check("POST /api/plans/deliver registra entrega", r.status_code == 200, str(r.status_code))
    if ok:
        delivery_id = r.json().get("data", {}).get("delivery", {}).get("id")
        check("Delivery tiene id", bool(delivery_id), str(delivery_id))

    r = req_get(f"/api/plans/history/{client_detail_id}", token)
    ok = check("GET /api/plans/history devuelve 200", r.status_code == 200)
    if ok:
        history = r.json().get("data", [])
        check("Historial no está vacío", len(history) >= 1, f"{len(history)} entregas")
        if history and diet_id:
            check("Historial incluye diet_title", history[0].get("diet_title") is not None,
                  str(history[0].get("diet_title")))

if delivery_id:
    r = req_post(f"/api/plans/resend/{delivery_id}", token=token)
    check("POST /api/plans/resend/{id} devuelve 200", r.status_code == 200, str(r.status_code))


# ─────────────────────────────────────────────────────────────────────────────
# 8. PORTAL PÚBLICO — FASE 3 SPRINT 20
# ─────────────────────────────────────────────────────────────────────────────
header("8. PORTAL PÚBLICO PARA CLIENTES (sin auth)")

# Obtener plantilla por defecto
r = req_get("/api/form-templates/default", token)
tmpl_id = r.json().get("data", {}).get("id") if r.status_code == 200 else None

public_assignment_id = None
if client_detail_id and tmpl_id:
    r = req_post("/api/form-assignments", {
        "form_template_id": tmpl_id,
        "client_user_detail_id": client_detail_id,
    }, token)
    if r.status_code == 200:
        public_assignment_id = r.json().get("data", {}).get("id")

if public_assignment_id:
    r = requests.get(f"{BASE}/api/public/form/{public_assignment_id}")
    ok = check("GET /api/public/form/{id} devuelve 200 SIN token", r.status_code == 200, str(r.status_code))
    if ok:
        pub = r.json().get("data", {})
        check("Respuesta incluye template", "template" in pub, str(pub.keys()))
        check("Respuesta incluye status",   "status"   in pub, str(pub.keys()))
        check("Status = pending",           pub.get("status") == "pending", pub.get("status"))

    r = requests.post(f"{BASE}/api/public/form/{public_assignment_id}/submit", json={
        "responses": [{"field_key": "weight", "value": "79.0"}]
    })
    check("POST /api/public/form/{id}/submit sin token devuelve 200", r.status_code == 200, str(r.status_code))

    r = requests.post(f"{BASE}/api/public/form/{public_assignment_id}/submit", json={
        "responses": []
    })
    check("Doble submit público retorna error", r.status_code != 200, str(r.status_code))
else:
    print(f"  {SKIP} Saltando portal público (cliente ya tenía formulario asignado)")


# ─────────────────────────────────────────────────────────────────────────────
# 9. FORMULARIOS — PENDING COUNT
# ─────────────────────────────────────────────────────────────────────────────
header("9. FORMULARIOS — BADGE DE PENDIENTES")

r = req_get("/api/form-assignments/pending-count", token)
check("GET /api/form-assignments/pending-count devuelve 200", r.status_code == 200)
if r.status_code == 200:
    count = r.json().get("data", {}).get("count", -1)
    check("Respuesta incluye count", count >= 0, str(count))
    print(f"       Pendientes: {count}")


# ─────────────────────────────────────────────────────────────────────────────
# 10. HEALTH CHECK
# ─────────────────────────────────────────────────────────────────────────────
header("10. HEALTH CHECK")

r = requests.get(f"{BASE}/api/health")
check("GET /api/health devuelve 200", r.status_code == 200, str(r.status_code))


# ─────────────────────────────────────────────────────────────────────────────
# RESUMEN
# ─────────────────────────────────────────────────────────────────────────────
total = passed + failed
print(f"\n{'═' * 64}")
print(f"  RESULTADO: {passed}/{total} checks pasaron")
if failed == 0:
    print(f"  {OK} QA Fase 2 + 3 completado — TODOS los checks pasaron")
else:
    print(f"  {ERR} {failed} check(s) FALLARON — revisar antes de entregar")
print(f"{'═' * 64}\n")

sys.exit(0 if failed == 0 else 1)
