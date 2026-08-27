"""Otros nombres (sinónimos) de un ejercicio.

El mismo ejercicio se llama de varias formas: "Press de banca", "bench press",
"press banca plano". El catálogo solo guardaba uno, así que quien buscaba por
cualquiera de los otros no encontraba nada — y lo normal entonces es crearlo
otra vez, que es como un catálogo común acaba con el mismo ejercicio tres veces.

Lo que hay que dejar sujeto:

  · Los sinónimos existen SOLO para buscar. Si la búsqueda no los mira, el
    campo es un cuadro de texto decorativo.
  · El ejercicio se sigue llamando `name` en todas partes. Encontrarlo por
    "bench press" no puede hacer que se muestre como "bench press".
  · Y no pueden saltarse el reparto por organización: encontrar por sinónimo un
    ejercicio privado de otro centro es la misma fuga que encontrarlo por su
    nombre, solo que por una puerta nueva.
"""
import uuid

from app.database import SessionLocal
from app.models.training import Training

from tests.test_org_scope import _crear_coach, _crear_organizacion


def _crear(client, headers, nombre, aliases=None):
    r = client.post("/api/trainings", headers=headers,
                    json={"name": nombre, "aliases": aliases})
    assert r.status_code == 200, r.text
    return r.json()["data"]["id"]


def _buscar(client, headers, texto):
    r = client.get(f"/api/trainings/search?search={texto}&per_page=100", headers=headers)
    assert r.status_code == 200, r.text
    return [t["name"] for t in r.json()["data"]["data"]]


# ── Para lo que existe el campo ────────────────────────────────────────────

def test_SE_ENCUENTRA_POR_UN_SINONIMO(client, seed, admin_headers):
    """Lo único que hace útil al campo."""
    suf = uuid.uuid4().hex[:8]
    _crear(client, admin_headers, f"Press de banca {suf}",
           "Bench press, Press banca plano")

    assert any(suf in n for n in _buscar(client, admin_headers, "Bench press")), \
        "no se encuentra por el sinónimo"
    assert any(suf in n for n in _buscar(client, admin_headers, "banca plano")), \
        "no se encuentra por el segundo sinónimo"


def test_encontrarlo_por_el_sinonimo_no_le_cambia_el_nombre(client, seed, admin_headers):
    """Se busca por "bench press" y el ejercicio sigue siendo "Press de banca":
    el sinónimo es una puerta de entrada, no otro nombre para mostrar."""
    suf = uuid.uuid4().hex[:8]
    _crear(client, admin_headers, f"Press de banca {suf}", "Bench press")

    encontrados = [n for n in _buscar(client, admin_headers, "Bench press") if suf in n]
    assert encontrados == [f"Press de banca {suf}"], encontrados


def test_el_nombre_de_siempre_sigue_encontrandose(client, seed, admin_headers):
    """Añadir una condición a un OR es la forma clásica de romper la de al lado."""
    suf = uuid.uuid4().hex[:8]
    _crear(client, admin_headers, f"Sentadilla {suf}", "Squat")
    assert any(suf in n for n in _buscar(client, admin_headers, f"Sentadilla {suf}"))


def test_un_ejercicio_sin_sinonimos_no_estorba(client, seed, admin_headers):
    """`aliases` es NULL en todos los que ya existen. Un ILIKE contra NULL no
    casa, pero tampoco puede tirar de la lista a los que sí tienen nombre."""
    suf = uuid.uuid4().hex[:8]
    _crear(client, admin_headers, f"Zancada {suf}")          # sin sinónimos
    assert any(suf in n for n in _buscar(client, admin_headers, f"Zancada {suf}"))
    assert not [n for n in _buscar(client, admin_headers, "xyzzy") if suf in n]


# ── Que se guarde y se devuelva ────────────────────────────────────────────

def test_los_sinonimos_se_guardan_y_se_leen(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    tid = _crear(client, admin_headers, f"Peso muerto {suf}", "Deadlift, PM")

    r = client.get(f"/api/trainings/{tid}/edit", headers=admin_headers)
    assert r.json()["data"]["aliases"] == "Deadlift, PM", r.json()["data"]

    db = SessionLocal()
    try:
        assert db.query(Training).filter(Training.id == tid).first().aliases == "Deadlift, PM"
    finally:
        db.close()


def test_SE_PUEDEN_QUITAR_los_sinonimos(client, seed, admin_headers):
    """Un campo que se puede escribir y no vaciar es un campo a medias."""
    suf = uuid.uuid4().hex[:8]
    tid = _crear(client, admin_headers, f"Remo {suf}", "Row")

    r = client.put(f"/api/trainings/{tid}/update", headers=admin_headers,
                   json={"aliases": None})
    assert r.status_code == 200, r.text
    assert not [n for n in _buscar(client, admin_headers, "Row") if suf in n]


def test_editar_otra_cosa_no_borra_los_sinonimos(client, seed, admin_headers):
    """`exclude_unset` es lo que separa "no lo mando" de "ponlo a vacío". Sin
    eso, cambiar el grupo muscular se llevaba por delante lo escrito."""
    suf = uuid.uuid4().hex[:8]
    tid = _crear(client, admin_headers, f"Curl {suf}", "Biceps curl")

    client.put(f"/api/trainings/{tid}/update", headers=admin_headers,
               json={"description": "Codos pegados"})
    r = client.get(f"/api/trainings/{tid}/edit", headers=admin_headers)
    assert r.json()["data"]["aliases"] == "Biceps curl", r.json()["data"]


# ── Y que no abran una puerta nueva a lo ajeno ─────────────────────────────

def test_EL_SINONIMO_NO_SALTA_EL_REPARTO_POR_ORGANIZACION(client, seed, admin_headers):
    """Encontrar por sinónimo un ejercicio privado de otro centro es la misma
    fuga de siempre, solo que por una puerta que acaba de abrirse."""
    suf = uuid.uuid4().hex[:8]
    _u1, det1, h1 = _crear_coach(client, admin_headers, f"coach.sin.a.{suf}@nutrientrena-qa.com")
    _crear_organizacion(det1, f"Centro A {suf}")
    _u2, det2, h2 = _crear_coach(client, admin_headers, f"coach.sin.b.{suf}@nutrientrena-qa.com")
    _crear_organizacion(det2, f"Centro B {suf}")

    _crear(client, h1, f"Secreto {suf}", "Hip thrust")

    assert any(suf in n for n in _buscar(client, h1, "Hip thrust")), "el suyo no lo ve"
    assert not [n for n in _buscar(client, h2, "Hip thrust") if suf in n], \
        "el coach del otro centro encuentra un ejercicio que no es suyo"
