"""Sección "Contenido global" del panel de plataforma.

Es la base de fábrica de Alzum: lo que toda cuenta nueva encuentra ya hecho.
Dos familias de contenido, y la diferencia es lo que se prueba aquí:

- Rutinas, ejercicios, dietas y alimentos TIENEN organización. Existe lo de
  plataforma (organization_id NULL) y lo privado de cada cuenta. La lista
  global no puede mezclarlos, porque entonces el super-admin creería que la
  base común incluye cosas que solo ve una cuenta.
- Grupos musculares, tipos de dieta y grupos de alimentos NO tienen dueño: son
  la fuente única de verdad. Se editan desde el panel y desde ningún otro
  sitio, y borrarlos cuando algo los usa rompería la librería de gente que no
  se ha enterado.
"""
from app.core.dependencies import EDITOR_CONTENIDO_GLOBAL, SOPORTE
from app.database import SessionLocal
from app.models.muscle_group import MuscleGroup
from app.models.nutrition.group_food import GroupFood
from app.models.training import Training

from tests.test_admin_panel import _con_rol
from tests.test_org_scope import _crear_organizacion, _crear_usuario


def _contenido(client, headers, tipo="routines", q=None):
    url = f"/api/admin/content?tipo={tipo}" + (f"&q={q}" if q else "")
    r = client.get(url, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()["data"]


def _nombres(datos):
    return [i["nombre"] for i in datos["items"]]


# ── Quién entra ─────────────────────────────────────────────────────────────

def test_el_editor_de_contenido_global_es_quien_manda_aqui(client, seed, admin_headers):
    """Es literalmente su trabajo: el catálogo maestro."""
    _uid, _det, h = _con_rol(client, admin_headers, "editor.cont.panel@nutrientrena-qa.com",
                             EDITOR_CONTENIDO_GLOBAL)
    assert client.get("/api/admin/content?tipo=routines", headers=h).status_code == 200


def test_soporte_no_toca_el_catalogo(client, seed, admin_headers):
    """Su sección es soporte, no la base de contenido de la plataforma."""
    _uid, _det, h = _con_rol(client, admin_headers, "soporte.cont@nutrientrena-qa.com", SOPORTE)
    assert client.get("/api/admin/content?tipo=routines", headers=h).status_code == 403


def test_un_coach_no_entra(client, seed, admin_headers):
    _uid, _det, h = _crear_usuario(client, admin_headers, "coach.cont.fuera@nutrientrena-qa.com", role_id=5)
    assert client.get("/api/admin/content?tipo=routines", headers=h).status_code == 403


def test_un_tipo_inventado_se_rechaza(client, seed, admin_headers):
    r = client.get("/api/admin/content?tipo=loquesea", headers=admin_headers)
    assert r.status_code == 400, r.text


# ── Global y privado no se mezclan ──────────────────────────────────────────

def test_la_lista_global_solo_trae_contenido_de_plataforma(client, seed, admin_headers):
    """Lo importante de toda la sección: si se colara lo privado de una
    cuenta, el super-admin creería que la base común lo incluye."""
    _uid, det, h = _crear_usuario(client, admin_headers, "coach.cont.privado@nutrientrena-qa.com", role_id=5)
    _crear_organizacion(det, "Centro con ejercicio privado")

    # El coach crea dentro de su organización; el super-admin, en plataforma.
    privado = client.post("/api/trainings", headers=h, json={"name": "Ejercicio privado del centro"})
    assert privado.status_code == 200, privado.text
    client.post("/api/trainings", headers=admin_headers, json={"name": "Ejercicio de fábrica"})

    datos = _contenido(client, admin_headers, "trainings")
    assert "Ejercicio de fábrica" in _nombres(datos)
    assert "Ejercicio privado del centro" not in _nombres(datos)
    assert all(i["origen"] == "plataforma" for i in datos["items"])


def test_el_contenido_de_las_cuentas_se_lista_aparte_y_con_su_cuenta(client, seed, admin_headers):
    _uid, det, h = _crear_usuario(client, admin_headers, "coach.cont.cuenta@nutrientrena-qa.com", role_id=5)
    org_id = _crear_organizacion(det, "Centro Contenido Aparte")
    client.post("/api/trainings", headers=h, json={"name": "Ejercicio solo de este centro"})

    datos = _contenido(client, admin_headers, "organizaciones")
    fila = next((i for i in datos["items"] if i["nombre"] == "Ejercicio solo de este centro"), None)
    assert fila is not None, _nombres(datos)
    assert fila["organization_id"] == org_id
    assert fila["organization_name"] == "Centro Contenido Aparte"
    assert fila["origen"] == "organizacion"


def test_los_conteos_separan_lo_global_de_lo_de_cuentas(client, seed, admin_headers):
    _uid, det, h = _crear_usuario(client, admin_headers, "coach.cont.conteos@nutrientrena-qa.com", role_id=5)
    _crear_organizacion(det, "Centro que suma al conteo")

    antes = _contenido(client, admin_headers, "trainings")["conteos"]["trainings"]
    client.post("/api/trainings", headers=h, json={"name": "Suma a cuentas"})
    client.post("/api/trainings", headers=admin_headers, json={"name": "Suma a global"})
    despues = _contenido(client, admin_headers, "trainings")["conteos"]["trainings"]

    assert despues["global"] == antes["global"] + 1
    assert despues["cuentas"] == antes["cuentas"] + 1


def test_los_catalogos_sin_dueno_no_cuentan_contenido_de_cuentas(client, seed, admin_headers):
    """No tienen organization_id: todo lo que hay ahí ya es global."""
    conteos = _contenido(client, admin_headers, "muscle_groups")["conteos"]
    for t in ["muscle_groups", "type_foods", "group_foods"]:
        assert conteos[t]["organizacion"] is False
        assert conteos[t]["cuentas"] == 0


def test_se_puede_buscar_por_nombre(client, seed, admin_headers):
    client.post("/api/trainings", headers=admin_headers, json={"name": "Zancada búlgara global"})
    datos = _contenido(client, admin_headers, "trainings", q="búlgara")
    assert "Zancada búlgara global" in _nombres(datos)
    assert all("búlgara" in n.lower() for n in _nombres(datos)), _nombres(datos)


# ── Catálogos: crear, renombrar, borrar ─────────────────────────────────────

def test_crear_renombrar_y_borrar_una_entrada_de_catalogo(client, seed, admin_headers):
    r = client.post("/api/admin/content/muscle_groups", headers=admin_headers,
                    json={"name": "Isquiotibiales de prueba"})
    assert r.status_code == 200, r.text
    gid = r.json()["data"]["id"]
    assert "Isquiotibiales de prueba" in _nombres(_contenido(client, admin_headers, "muscle_groups"))

    r = client.put(f"/api/admin/content/muscle_groups/{gid}", headers=admin_headers,
                   json={"name": "Isquiosurales"})
    assert r.status_code == 200, r.text
    nombres = _nombres(_contenido(client, admin_headers, "muscle_groups"))
    assert "Isquiosurales" in nombres and "Isquiotibiales de prueba" not in nombres

    assert client.delete(f"/api/admin/content/muscle_groups/{gid}", headers=admin_headers).status_code == 200
    assert "Isquiosurales" not in _nombres(_contenido(client, admin_headers, "muscle_groups"))


def test_no_se_repite_el_nombre_en_un_catalogo(client, seed, admin_headers):
    client.post("/api/admin/content/group_foods", headers=admin_headers, json={"name": "Legumbres QA"})
    r = client.post("/api/admin/content/group_foods", headers=admin_headers, json={"name": "Legumbres QA"})
    assert r.status_code == 400, r.text


def test_no_se_borra_un_catalogo_que_alguien_esta_usando(client, seed, admin_headers):
    """Borrar un grupo muscular que usan ejercicios de varias cuentas no es
    limpiar: es romperle la librería a gente que no se ha enterado."""
    db = SessionLocal()
    try:
        g = MuscleGroup(name="Grupo en uso QA")
        db.add(g)
        db.commit()
        db.refresh(g)
        gid = g.id
        db.add(Training(name="Ejercicio que usa el grupo", muscle_group_id=gid, state=1))
        db.commit()
    finally:
        db.close()

    r = client.delete(f"/api/admin/content/muscle_groups/{gid}", headers=admin_headers)
    assert r.status_code == 400, r.text
    assert "usando" in r.json()["message"].lower()

    # Y sigue ahí
    assert "Grupo en uso QA" in _nombres(_contenido(client, admin_headers, "muscle_groups"))


def test_lo_que_tiene_organizacion_no_se_crea_desde_aqui(client, seed, admin_headers):
    """Una rutina se hace en su constructor, no con un campo "nombre" en el
    panel. Ofrecerlo aquí sería un segundo editor a medias."""
    for tipo in ["routines", "trainings", "diets", "aliments"]:
        r = client.post(f"/api/admin/content/{tipo}", headers=admin_headers, json={"name": "X"})
        assert r.status_code == 400, (tipo, r.text)


def test_el_editor_global_tambien_mantiene_los_catalogos(client, seed, admin_headers):
    _uid, _det, h = _con_rol(client, admin_headers, "editor.cont.catalogo@nutrientrena-qa.com",
                             EDITOR_CONTENIDO_GLOBAL)
    r = client.post("/api/admin/content/type_foods", headers=h, json={"name": "Dieta QA del editor"})
    assert r.status_code == 200, r.text


def test_un_coach_no_puede_tocar_los_catalogos(client, seed, admin_headers):
    _uid, _det, h = _crear_usuario(client, admin_headers, "coach.cont.catalogo@nutrientrena-qa.com", role_id=5)
    assert client.post("/api/admin/content/muscle_groups", headers=h,
                       json={"name": "Grupo colado"}).status_code == 403

    db = SessionLocal()
    try:
        g = GroupFood(name="Grupo alimentos QA coach")
        db.add(g)
        db.commit()
        db.refresh(g)
        gid = g.id
    finally:
        db.close()
    assert client.delete(f"/api/admin/content/group_foods/{gid}", headers=h).status_code == 403


# ── Lo que no se inventa ────────────────────────────────────────────────────

def test_las_propuestas_llegan_en_null_porque_no_existe_el_circuito(client, seed, admin_headers):
    """El prototipo enseña una cola de aprobación; el circuito (que un coach
    proponga y quede registrado) no está hecho. Devolver 0 diría "no hay
    ninguna", que no es lo mismo que "todavía no existe"."""
    assert _contenido(client, admin_headers)["totales"]["propuestas"] is None
