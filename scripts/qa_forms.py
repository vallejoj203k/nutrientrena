"""
QA Sprint 10 - Flujo completo del módulo Forms.

Uso:
  python scripts/qa_forms.py

Variables de entorno (opcional, tienen defaults):
  API_URL   -> URL base de la API  (default: http://localhost:8000)
  ADMIN_EMAIL, ADMIN_PASSWORD      (default: admin@nutrientrena.com / Admin123!)
"""
import os
import sys
import json

try:
    import requests
except ImportError:
    print("ERROR: pip install requests")
    sys.exit(1)

BASE     = os.environ.get("API_URL", "http://localhost:8000")
EMAIL    = os.environ.get("ADMIN_EMAIL", "admin@nutrientrena.com")
PASSWORD = os.environ.get("ADMIN_PASSWORD", "Admin123!")

OK  = "✅"
ERR = "❌"
SEP = "─" * 60


def h(title):
    print(f"\n{SEP}\n{title}\n{SEP}")


def check(label, condition, detail=""):
    mark = OK if condition else ERR
    msg = f"{mark} {label}"
    if detail:
        msg += f"  →  {detail}"
    print(msg)
    if not condition:
        sys.exit(1)


def post(path, body, token=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return requests.post(f"{BASE}{path}", json=body, headers=headers)


def get(path, token=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return requests.get(f"{BASE}{path}", headers=headers)


# ── 1. Login ──────────────────────────────────────────────────────────────────
h("1. LOGIN")
r = post("/api/auth/login", {"email": EMAIL, "password": PASSWORD})
check("POST /api/auth/login devuelve 200", r.status_code == 200, str(r.status_code))
token = r.json().get("data", {}).get("access_token")
check("Respuesta incluye access_token", bool(token))

# ── 2. GET /api/auth/me ───────────────────────────────────────────────────────
h("2. ME")
r = get("/api/auth/me", token)
check("GET /api/auth/me devuelve 200", r.status_code == 200, str(r.status_code))
me = r.json().get("data", {})
admin_user_id = me.get("id")
check("Me devuelve id de usuario", bool(admin_user_id), str(admin_user_id))
print(f"   Admin: {me.get('name')} ({me.get('email')})")

# ── 3. Formulario por defecto ─────────────────────────────────────────────────
h("3. FORM TEMPLATE DEFAULT")
r = get("/api/form-templates/default", token)
check("GET /api/form-templates/default devuelve 200", r.status_code == 200, str(r.status_code))
tmpl = r.json().get("data", {})
tmpl_id = tmpl.get("id")
fields  = tmpl.get("fields", [])
check("Plantilla por defecto existe", bool(tmpl_id), str(tmpl_id))
check("Plantilla tiene al menos 10 campos", len(fields) >= 10, str(len(fields)))
print(f"   Plantilla: '{tmpl.get('title')}' — {len(fields)} campos")
print(f"   Campos: {[f['field_key'] for f in fields]}")

# ── 4. Crear cliente de prueba ────────────────────────────────────────────────
h("4. CREAR CLIENTE")
import time
ts = int(time.time())
r = post("/api/users", {
    "name": f"QA Cliente {ts}",
    "email": f"qa.cliente.{ts}@test.com",
    "password": "Test1234!",
    "role_id": 6,
}, token)
check("POST /api/users devuelve 200 o 201", r.status_code in (200, 201), str(r.status_code))
client_data = r.json().get("data", {})
client_detail_id = client_data.get("detail", {}).get("id") or client_data.get("user_detail_id")
client_user_id   = client_data.get("id")
check("Respuesta incluye detail.id (UserDetail UUID)", bool(client_detail_id), str(client_detail_id))
print(f"   Cliente creado: id={client_user_id}, detail_id={client_detail_id}")

# ── 5. Asignar formulario ─────────────────────────────────────────────────────
h("5. ASIGNAR FORMULARIO")
r = post("/api/form-assignments", {
    "form_template_id": tmpl_id,
    "client_user_detail_id": client_detail_id,
}, token)
check("POST /api/form-assignments devuelve 200", r.status_code == 200, str(r.status_code))
assignment = r.json().get("data", {})
assignment_id = assignment.get("id")
check("Assignment creado con UUID", bool(assignment_id), str(assignment_id))
check("Status = pending", assignment.get("status") == "pending", assignment.get("status"))
print(f"   Assignment id={assignment_id}")

# ── 6. Verificar estado cliente → Formulario pendiente ────────────────────────
h("6. ESTADO CLIENTE TRAS ASIGNACIÓN")
r = get(f"/api/users/{client_user_id}", token)
check("GET /api/users/{id} devuelve 200", r.status_code == 200, str(r.status_code))
udata = r.json().get("data", {})
status_id = udata.get("detail", {}).get("status_id")
check("status_id fue actualizado (no None)", status_id is not None, str(status_id))
print(f"   status_id del cliente = {status_id}  (debe ser 'Formulario pendiente')")

# ── 7. Comprobar que no se puede asignar otro formulario pendiente ─────────────
h("7. DOBLE ASIGNACIÓN (debe fallar)")
r = post("/api/form-assignments", {
    "form_template_id": tmpl_id,
    "client_user_detail_id": client_detail_id,
}, token)
check("Segunda asignación retorna error (no 200)", r.status_code != 200, str(r.status_code))
print(f"   Respuesta: {r.json().get('message', r.text)}")

# ── 8. Enviar formulario ──────────────────────────────────────────────────────
h("8. SUBMIT FORMULARIO")
r = post(f"/api/form-assignments/{assignment_id}/submit", {
    "responses": [
        {"field_key": "weight",       "value": "78.5"},
        {"field_key": "height",       "value": "175"},
        {"field_key": "phone",        "value": "+34 600 000 001"},
        {"field_key": "occupation",   "value": "Ingeniero"},
        {"field_key": "injuries",     "value": "Ninguna"},
        {"field_key": "experience",   "value": "2 años en gym"},
        {"field_key": "motivation",   "value": "Mejorar salud"},
    ]
}, token)
check("POST /api/form-assignments/{id}/submit devuelve 200", r.status_code == 200, str(r.status_code))
submitted = r.json().get("data", {})
check("Status = submitted", submitted.get("status") == "submitted", submitted.get("status"))
check("submitted_at no es None", submitted.get("submitted_at") is not None, str(submitted.get("submitted_at")))

# ── 9. Verificar perfil actualizado ──────────────────────────────────────────
h("9. PERFIL CLIENTE ACTUALIZADO")
r = get(f"/api/users/{client_user_id}", token)
check("GET /api/users/{id} devuelve 200", r.status_code == 200)
detail = r.json().get("data", {}).get("detail", {})
check("weight actualizado a 78.5", str(detail.get("weight")) == "78.5", str(detail.get("weight")))
check("height actualizado a 175.0", str(detail.get("height")) in ("175.0", "175"), str(detail.get("height")))
check("phone actualizado", detail.get("phone") == "+34 600 000 001", str(detail.get("phone")))
status_id_after = detail.get("status_id")
check("status_id fue actualizado tras submit", status_id_after is not None, str(status_id_after))
print(f"   status_id tras submit = {status_id_after}  (debe ser 'Formulario recibido')")

# ── 10. Doble submit (debe fallar) ────────────────────────────────────────────
h("10. DOBLE SUBMIT (debe fallar)")
r = post(f"/api/form-assignments/{assignment_id}/submit", {"responses": []}, token)
check("Segundo submit retorna error", r.status_code != 200, str(r.status_code))
print(f"   Respuesta: {r.json().get('message', r.text)}")

# ── 11. Respuestas guardadas ──────────────────────────────────────────────────
h("11. RESPUESTAS GUARDADAS")
r = get(f"/api/form-assignments/{assignment_id}/responses", token)
check("GET /api/form-assignments/{id}/responses devuelve 200", r.status_code == 200)
responses = r.json().get("data", {}).get("responses", [])
check("Respuestas guardadas en BD", len(responses) >= 7, str(len(responses)))
print(f"   {len(responses)} respuestas guardadas")

# ── 12. GET /api/form-assignments/pending ─────────────────────────────────────
h("12. ASSIGNMENTS PENDIENTES")
r = get("/api/form-assignments/pending", token)
check("GET /api/form-assignments/pending devuelve 200", r.status_code == 200)

# ── 13. GET /api/form-templates (lista) ───────────────────────────────────────
h("13. LISTA DE PLANTILLAS")
r = get("/api/form-templates", token)
check("GET /api/form-templates devuelve 200", r.status_code == 200)
templates = r.json().get("data", [])
check("Al menos 1 plantilla", len(templates) >= 1, str(len(templates)))

# ── Resumen ───────────────────────────────────────────────────────────────────
print(f"\n{SEP}")
print(f"{OK} Sprint 10 QA completado — todos los checks pasaron")
print(f"{SEP}\n")
