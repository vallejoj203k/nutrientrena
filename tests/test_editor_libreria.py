"""El editor de contenido global mantiene la Librería entera.

El rol se creó cuando el panel de plataforma no existía: su única puerta era el
panel del coach, y allí se le recortó el menú a dos pantallas —alimentos y
ejercicios—. Ahora su sección "Contenido global" ES la Librería completa, así
que necesita poder trabajar en todas: rutinas, dietas, recetas, menús,
catálogos, formularios, programas y documentos.

La línea es la misma en todos los casos y es la que separa su rol del de un
coach: **la biblioteca sí, los clientes no**. Puede crear una rutina de
plataforma; no puede ver la lista de clientes, ni asignarles nada, ni mandarles
un documento. Estos tests fijan las dos mitades, porque abrir permisos sin
comprobar lo que sigue cerrado es como no comprobar nada.
"""
import uuid

from tests.test_org_scope import _crear_usuario


def _editor(client, admin_headers, suf):
    from app.core.dependencies import EDITOR_CONTENIDO_GLOBAL
    from app.database import SessionLocal
    from app.seeds.roles import seed_roles

    db = SessionLocal()
    try:
        seed_roles(db)
    finally:
        db.close()
    _uid, _det, h = _crear_usuario(client, admin_headers,
                                   f"editor.lib.{suf}@nutrientrena-qa.com",
                                   role_id=EDITOR_CONTENIDO_GLOBAL)
    return h


# ── La biblioteca: sí ──────────────────────────────────────────────────────

LECTURAS = [
    "/api/routines/findAll",
    "/api/trainings/findAll",
    "/api/diets/findAll",
    "/api/aliments/findAll",
    "/api/recipes/findAll",
    "/api/weekly-menus",
    "/api/muscle-groups/findAll",
    "/api/type-foods/findAll",
    "/api/group-foods/findAll",
    "/api/parameters/search",
    "/api/form-templates",
    "/api/programs",
    "/api/contracts/templates",
    "/api/documents",
]


def test_el_editor_puede_abrir_las_pantallas_de_la_libreria(client, seed, admin_headers):
    """Antes de esto, la mitad respondían 403 y la pantalla salía vacía con un
    "Error al cargar" que no decía por qué."""
    h = _editor(client, admin_headers, uuid.uuid4().hex[:8])
    fallan = [ruta for ruta in LECTURAS if client.get(ruta, headers=h).status_code == 403]
    assert not fallan, fallan


def test_el_editor_crea_contenido_de_plataforma(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    h = _editor(client, admin_headers, suf)

    r = client.post("/api/routines", headers=h, json={"name": f"Rutina del editor {suf}"})
    assert r.status_code == 200, r.text
    # Sin organización propia, lo que crea nace en el catálogo común: es
    # justamente su trabajo.
    assert r.json()["data"]["organization_id"] is None, r.json()["data"]


def test_y_puede_hacerlo_actuando_como_la_plataforma(client, seed, admin_headers):
    """La Librería abierta desde su panel manda la cabecera de plataforma. Si no
    se le admitiera, cada pantalla le respondería 403."""
    suf = uuid.uuid4().hex[:8]
    h = dict(_editor(client, admin_headers, suf))
    h["X-Organization-Id"] = "plataforma"

    r = client.get("/api/routines/findAll", headers=h)
    assert r.status_code == 200, r.text
    assert all(x.get("organization_id") is None for x in r.json()["data"])


def test_el_editor_puede_subir_imagenes(client, seed, admin_headers):
    """Las fotos de los ejercicios las sube él: es media hora de su trabajo.

    Faltaba el permiso, así que se llevaba un 403 que la pantalla enseñaba como
    "Error al subir imagen", sin decir que era de permisos. Un CLIENTE podía
    subir foto de perfil y el editor de contenido no.

    No se comprueba que la subida termine bien —eso depende del almacenamiento,
    que en las pruebas no existe— sino que la PUERTA sea la misma que para un
    coach: si a él le dejan pasar y al editor no, es un problema de permisos.
    """
    suf = uuid.uuid4().hex[:8]
    h_editor = _editor(client, admin_headers, suf)
    _uid, _det, h_coach = _crear_usuario(client, admin_headers,
                                         f"coach.sube.{suf}@nutrientrena-qa.com", role_id=5)

    # Un PNG de 1x1: lo mínimo que el servidor acepta como imagen de verdad.
    png = (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
           b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\xdac\xfc\xcf"
           b"\xc0P\x0f\x00\x04\x85\x01\x80\x84\xa9\x8c!\x00\x00\x00\x00IEND\xaeB`\x82")
    fichero = {"file": ("pixel.png", png, "image/png")}

    r_editor = client.post("/api/files/upload", headers=h_editor, files=fichero)
    r_coach = client.post("/api/files/upload", headers=h_coach, files=fichero)

    assert r_editor.status_code != 403, r_editor.text
    assert r_editor.status_code == r_coach.status_code, (r_editor.status_code, r_coach.status_code)


# ── Los clientes: no ───────────────────────────────────────────────────────

def test_el_editor_no_ve_la_lista_de_clientes(client, seed, admin_headers):
    h = _editor(client, admin_headers, uuid.uuid4().hex[:8])
    assert client.get("/api/users/client/findAll", headers=h).status_code == 403


def test_el_editor_no_asigna_contenido_a_nadie(client, seed, admin_headers):
    """Lo que de verdad separa su rol del de un coach."""
    h = _editor(client, admin_headers, uuid.uuid4().hex[:8])
    prohibidos = [
        ("post", "/api/routines/assigned", {}),
        ("post", "/api/recipes/assign", {}),
        ("post", "/api/form-assignments", {}),
    ]
    for metodo, ruta, cuerpo in prohibidos:
        r = getattr(client, metodo)(ruta, headers=h, json=cuerpo)
        assert r.status_code == 403, (ruta, r.status_code)


def test_el_editor_no_ve_los_contratos_enviados_a_clientes(client, seed, admin_headers):
    """Las PLANTILLAS de contrato sí las mantiene; los contratos firmados por
    los clientes de un coach son otra cosa."""
    h = _editor(client, admin_headers, uuid.uuid4().hex[:8])
    assert client.get("/api/contracts/templates", headers=h).status_code == 200
    assert client.get("/api/contracts", headers=h).status_code == 403


def test_el_editor_sigue_sin_entrar_donde_no_le_toca(client, seed, admin_headers):
    h = _editor(client, admin_headers, uuid.uuid4().hex[:8])
    for ruta in ("/api/admin/organizations", "/api/admin/team", "/api/admin/plans"):
        assert client.get(ruta, headers=h).status_code == 403, ruta
