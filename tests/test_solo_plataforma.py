"""Ver SOLO el catálogo de la plataforma, no la biblioteca entera.

Un super-admin sin contexto de organización ve TODO: lo de la plataforma y lo
privado de cada cuenta. Para administrar está bien; para mantener el catálogo
común, no: quien entra por "Contenido global" espera ver el catálogo común y
solo eso, y sin embargo se encontraba mezclado el contenido privado de cada
coach, sin nada en la pantalla que lo dijera.

La Librería abierta desde el panel de plataforma manda `X-Organization-Id:
plataforma` —un centinela, porque "sin organización" no es el id de ninguna— y
entonces los listados se quedan en `organization_id IS NULL`.

Se comprueba en los cinco tipos de contenido que tienen organización (rutinas,
ejercicios, dietas, alimentos, recetas) y no solo en uno: la regla vive en cada
router, así que un tipo podría quedarse fuera sin que nada avisara.
"""
import uuid

from app.database import SessionLocal
from app.models.nutrition.aliment import Aliment
from app.models.nutrition.diet import Diet
from app.models.nutrition.recipe import Recipe
from app.models.routine import Routine
from app.models.training import Training

from tests.test_org_scope import _crear_coach, _crear_organizacion, _crear_usuario

PLATAFORMA = {"X-Organization-Id": "plataforma"}


def _headers(base, extra=None):
    h = dict(base)
    if extra:
        h.update(extra)
    return h


def _contenido_de(org_id, sufijo):
    """Contenido privado de una cuenta, escrito directo en la base.

    Se crea así y no por API porque el objetivo es la LECTURA: lo que importa
    es que exista una fila con esa organización, no por qué puerta entró.
    """
    db = SessionLocal()
    try:
        db.add(Routine(name=f"Rutina privada {sufijo}", organization_id=org_id))
        db.add(Training(name=f"Ejercicio privado {sufijo}", state=1, organization_id=org_id))
        db.add(Diet(title=f"Dieta privada {sufijo}", organization_id=org_id))
        db.add(Aliment(name=f"Alimento privado {sufijo}", calories=100, organization_id=org_id))
        db.add(Recipe(name=f"Receta privada {sufijo}", organization_id=org_id))
        db.commit()
    finally:
        db.close()


def _catalogo_de_plataforma(sufijo):
    db = SessionLocal()
    try:
        db.add(Routine(name=f"Rutina de fábrica {sufijo}", organization_id=None))
        db.add(Training(name=f"Ejercicio de fábrica {sufijo}", state=1, organization_id=None))
        db.add(Diet(title=f"Dieta de fábrica {sufijo}", organization_id=None))
        db.add(Aliment(name=f"Alimento de fábrica {sufijo}", calories=100, organization_id=None))
        db.add(Recipe(name=f"Receta de fábrica {sufijo}", organization_id=None))
        db.commit()
    finally:
        db.close()


def _nombres(client, ruta, headers):
    r = client.get(ruta, headers=headers)
    assert r.status_code == 200, (ruta, r.text)
    datos = r.json()["data"]
    if isinstance(datos, dict):          # /search devuelve {data, total, ...}
        datos = datos.get("data", [])
    return [x.get("name") or x.get("title") for x in datos]


LISTADOS = [
    ("/api/routines/findAll", "Rutina"),
    ("/api/trainings/findAll", "Ejercicio"),
    ("/api/diets/findAll", "Dieta"),
    ("/api/aliments/findAll", "Alimento"),
    ("/api/recipes/findAll", "Receta"),
]


def test_sin_cabecera_el_superadmin_sigue_viendo_la_biblioteca_entera(client, seed, admin_headers):
    """La regla de siempre no cambia: administrar es ver todo."""
    suf = uuid.uuid4().hex[:8]
    _uid, det, _h = _crear_coach(client, admin_headers, f"coach.todo.{suf}@nutrientrena-qa.com")
    org_id = _crear_organizacion(det, f"Centro Todo {suf}")
    _contenido_de(org_id, suf)
    _catalogo_de_plataforma(suf)

    for ruta, tipo in LISTADOS:
        nombres = _nombres(client, ruta, admin_headers)
        assert f"{tipo} privada {suf}" in nombres or f"{tipo} privado {suf}" in nombres, (ruta, suf)


def test_como_plataforma_solo_se_ve_el_catalogo_comun(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    _uid, det, _h = _crear_coach(client, admin_headers, f"coach.solo.{suf}@nutrientrena-qa.com")
    org_id = _crear_organizacion(det, f"Centro Solo {suf}")
    _contenido_de(org_id, suf)
    _catalogo_de_plataforma(suf)

    h = _headers(admin_headers, PLATAFORMA)
    for ruta, tipo in LISTADOS:
        nombres = _nombres(client, ruta, h)
        # Lo de la plataforma sí, lo de la cuenta no. Las dos mitades importan:
        # sin la primera, un filtro que lo tapara todo también pasaría.
        assert (f"{tipo} de fábrica {suf}" in nombres), (ruta, nombres[:6])
        assert f"{tipo} privada {suf}" not in nombres, (ruta, nombres[:6])
        assert f"{tipo} privado {suf}" not in nombres, (ruta, nombres[:6])


def test_tambien_filtra_los_buscadores(client, seed, admin_headers):
    """El buscador es otra consulta distinta: si solo se hubiera arreglado el
    listado, escribir el nombre en la caja seguiría sacando lo privado."""
    suf = uuid.uuid4().hex[:8]
    _uid, det, _h = _crear_coach(client, admin_headers, f"coach.busca.{suf}@nutrientrena-qa.com")
    org_id = _crear_organizacion(det, f"Centro Busca {suf}")
    _contenido_de(org_id, suf)

    h = _headers(admin_headers, PLATAFORMA)
    for ruta in (f"/api/trainings/search?search={suf}", f"/api/aliments/search?search={suf}"):
        assert _nombres(client, ruta, h) == [], ruta


def test_no_se_puede_abrir_por_id_lo_privado_de_una_cuenta(client, seed, admin_headers):
    """Que no salga en la lista no basta: con el id a mano seguiría abriéndose."""
    suf = uuid.uuid4().hex[:8]
    _uid, det, _h = _crear_coach(client, admin_headers, f"coach.id.{suf}@nutrientrena-qa.com")
    org_id = _crear_organizacion(det, f"Centro Id {suf}")
    _contenido_de(org_id, suf)

    db = SessionLocal()
    try:
        rid = db.query(Routine).filter(Routine.name == f"Rutina privada {suf}").first().id
    finally:
        db.close()

    h = _headers(admin_headers, PLATAFORMA)
    assert client.get(f"/api/routines/{rid}/edit", headers=h).status_code in (403, 404)
    # Y sin la cabecera, el mismo super-admin sí puede: no se le ha quitado nada.
    assert client.get(f"/api/routines/{rid}/edit", headers=admin_headers).status_code == 200


def test_lo_que_se_crea_como_plataforma_nace_en_el_catalogo_comun(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    h = _headers(admin_headers, PLATAFORMA)
    r = client.post("/api/trainings", headers=h, json={"name": f"Ejercicio nuevo {suf}"})
    assert r.status_code == 200, r.text
    assert r.json()["data"]["organization_id"] is None, r.json()["data"]


def test_un_coach_no_puede_actuar_como_la_plataforma(client, seed, admin_headers):
    """La cabecera no puede ser una escalada: a quien no es plataforma se le
    dice que no, en vez de ignorársela y dejarle creyendo que ve el catálogo."""
    suf = uuid.uuid4().hex[:8]
    _uid, _det, hc = _crear_coach(client, admin_headers, f"coach.nope.{suf}@nutrientrena-qa.com")
    r = client.get("/api/trainings/findAll", headers=_headers(hc, PLATAFORMA))
    assert r.status_code == 403, r.text


def test_un_cliente_tampoco(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    _uid, _det, hc = _crear_usuario(client, admin_headers,
                                    f"cliente.nope.{suf}@nutrientrena-qa.com", role_id=6)
    r = client.get("/api/routines/findAll", headers=_headers(hc, PLATAFORMA))
    assert r.status_code in (401, 403), r.text
