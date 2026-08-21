"""Lo que está en el catálogo de la plataforma no lo borra un coach.

Un ejercicio, una dieta o un alimento del catálogo común lo usan TODAS las
cuentas. Que un coach cualquiera pueda borrarlo significa que un clic suyo se
lleva por delante el material de gente que no conoce.

El caso que hay que mirar con cuidado no es el evidente —un coach borrando algo
que nunca fue suyo— sino este otro:

    un coach crea un ejercicio → el superadmin lo sube a la plataforma
    → ¿puede el coach seguir borrándolo?

Y la respuesta tiene que ser NO. Subirlo cambia de quién es: pasa a ser
material común del que ya dependen otras cuentas. La regla de "quien lo creó
puede tocar lo suyo" existe para que un coach sin organización no se quede
bloqueado con su propio contenido, no para conservar una llave sobre algo que
ya entregó.
"""
import uuid

from app.database import SessionLocal

from tests.test_org_scope import _crear_coach, _crear_organizacion


def _coach(client, admin_headers, suf, nombre="coach"):
    _uid, det, h = _crear_coach(client, admin_headers, f"{nombre}.plat.{suf}@nutrientrena-qa.com")
    _crear_organizacion(det, f"Centro {nombre} {suf}")
    return h


def _subir_a_plataforma(client, admin_headers, tipo, id_):
    """Deja la pieza en el catálogo común. Lo que crea el superadmin ya nace
    ahí, y entonces la promoción responde 400: para lo que se prueba aquí, el
    resultado es el mismo."""
    r = client.put(f"/api/content/{tipo}/{id_}/organization",
                   headers=admin_headers, json={"organization_id": None})
    assert r.status_code == 200 or "ya es del catálogo" in r.text, r.text


# ── Ejercicios ──────────────────────────────────────────────────────────────

def test_un_coach_no_borra_un_ejercicio_de_la_plataforma(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    h_coach = _coach(client, admin_headers, suf)
    ej = client.post("/api/trainings", headers=admin_headers,
                     json={"name": f"Ejercicio comun {suf}"}).json()["data"]
    _subir_a_plataforma(client, admin_headers, "training", ej["id"])

    r = client.delete(f"/api/trainings/{ej['id']}", headers=h_coach)
    assert r.status_code == 403, r.text
    # Y sigue estando.
    assert client.get(f"/api/trainings/{ej['id']}/edit", headers=h_coach).status_code == 200


def test_subirlo_a_la_plataforma_le_quita_al_creador_el_poder_de_borrarlo(client, seed, admin_headers):
    """El caso de verdad: lo hizo él, pero ya no es suyo."""
    suf = uuid.uuid4().hex[:8]
    h_coach = _coach(client, admin_headers, suf)
    ej = client.post("/api/trainings", headers=h_coach,
                     json={"name": f"Sentadilla {suf}"}).json()["data"]

    # Mientras es suyo, puede con él.
    assert client.put(f"/api/trainings/{ej['id']}/update", headers=h_coach,
                      json={"name": f"Sentadilla bulgara {suf}"}).status_code == 200

    _subir_a_plataforma(client, admin_headers, "training", ej["id"])

    assert client.delete(f"/api/trainings/{ej['id']}", headers=h_coach).status_code == 403
    assert client.put(f"/api/trainings/{ej['id']}/update", headers=h_coach,
                      json={"name": "Otro nombre"}).status_code == 403


def test_pero_sigue_viendolo_y_usandolo(client, seed, admin_headers):
    """Quitarle el borrado no es quitarle el acceso: el catálogo común está
    para que lo use."""
    suf = uuid.uuid4().hex[:8]
    h_coach = _coach(client, admin_headers, suf)
    ej = client.post("/api/trainings", headers=h_coach,
                     json={"name": f"Peso muerto {suf}"}).json()["data"]
    _subir_a_plataforma(client, admin_headers, "training", ej["id"])

    r = client.get(f"/api/trainings/search?search={suf}", headers=h_coach)
    assert r.status_code == 200, r.text
    datos = r.json()["data"]
    filas = datos.get("data", datos) if isinstance(datos, dict) else datos
    assert any(f["id"] == ej["id"] for f in filas), filas


def test_su_propio_ejercicio_sin_subir_si_lo_borra(client, seed, admin_headers):
    """No se puede pasar de frenada: lo suyo es suyo."""
    suf = uuid.uuid4().hex[:8]
    h_coach = _coach(client, admin_headers, suf)
    ej = client.post("/api/trainings", headers=h_coach,
                     json={"name": f"Mio {suf}"}).json()["data"]
    assert client.delete(f"/api/trainings/{ej['id']}", headers=h_coach).status_code == 200


# ── Alimentos ───────────────────────────────────────────────────────────────

def test_un_alimento_subido_deja_de_ser_del_coach(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    h_coach = _coach(client, admin_headers, suf)
    al = client.post("/api/aliments", headers=h_coach,
                     json={"name": f"Avena {suf}", "calories": 350}).json()["data"]
    _subir_a_plataforma(client, admin_headers, "aliment", al["id"])

    assert client.delete(f"/api/aliments/{al['id']}", headers=h_coach).status_code == 403


# ── Dietas ──────────────────────────────────────────────────────────────────

def test_una_dieta_subida_deja_de_ser_del_coach(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    h_coach = _coach(client, admin_headers, suf)
    di = client.post("/api/diets", headers=h_coach,
                     json={"title": f"Volumen {suf}"}).json()["data"]
    _subir_a_plataforma(client, admin_headers, "diet", di["id"])

    assert client.delete(f"/api/diets/{di['id']}", headers=h_coach).status_code == 403


# ── Rutinas ─────────────────────────────────────────────────────────────────

def test_una_rutina_subida_deja_de_ser_del_coach(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    h_coach = _coach(client, admin_headers, suf)
    ru = client.post("/api/routines", headers=h_coach,
                     json={"name": f"Full body {suf}"}).json()["data"]
    _subir_a_plataforma(client, admin_headers, "routine", ru["id"])

    assert client.delete(f"/api/routines/{ru['id']}", headers=h_coach).status_code == 403


# ── Alzum sí puede ──────────────────────────────────────────────────────────

def test_el_superadmin_si_borra_lo_de_la_plataforma(client, seed, admin_headers):
    """Es suyo: alguien tiene que poder mantener el catálogo."""
    suf = uuid.uuid4().hex[:8]
    ej = client.post("/api/trainings", headers=admin_headers,
                     json={"name": f"Para borrar {suf}"}).json()["data"]
    _subir_a_plataforma(client, admin_headers, "training", ej["id"])
    assert client.delete(f"/api/trainings/{ej['id']}", headers=admin_headers).status_code == 200
