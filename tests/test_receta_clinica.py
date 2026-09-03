"""Lo que el nutricionista escribe de una receta, más allá de los macros.

La receta guardaba el nombre, los macros y poco más. Faltaba lo que decide si
le sirve o no a una persona concreta: qué alérgenos excluye, a qué estilo
pertenece, para qué patologías vale, y las notas del propio nutricionista.

Lo que hay que dejar sujeto:

  · Que todo eso se guarde y vuelva tal cual al abrir la receta.
  · Que las patologías sean LAS MISMAS que usan las dietas —un solo catálogo—
    y que se puedan cambiar sin tocar el resto.
  · Que una edición parcial no borre lo que no se ha tocado.
"""
import uuid

from app.database import SessionLocal
from app.models.nutrition.diet import Pathology

from tests.test_macros_porcion import _monta


CATALOGO = [
    ("Enfermedad celíaca", "Intolerancias"),
    ("Intolerancia a la lactosa", "Intolerancias"),
    ("SII / FODMAP", "Digestivo"),
    ("Diabetes tipo 2", "Metabólico"),
    ("Hipertensión", "Cardiovascular"),
]


def _asegura_catalogo():
    """El catálogo lo siembra la migración, que en el banco de pruebas no corre.

    Se añade lo que falte POR NOMBRE, no "solo si la tabla está vacía": el
    banco es el mismo para todas las pruebas, y con esa condición la primera
    que sembrara dejaría a las demás sin lo suyo según el orden de ejecución.
    """
    db = SessionLocal()
    try:
        hay = {p.name for p in db.query(Pathology).all()}
        nuevas = [Pathology(name=n, state=1, grupo=g) for n, g in CATALOGO if n not in hay]
        if nuevas:
            db.add_all(nuevas)
            db.commit()
    finally:
        db.close()


def _patologias(client, h):
    _asegura_catalogo()
    r = client.get("/api/pathologies/findAll", headers=h)
    assert r.status_code == 200, r.text
    return r.json()["data"]


def _crear(client, h, nombre, **campos):
    body = {"name": nombre}
    body.update(campos)
    r = client.post("/api/recipes", headers=h, json=body)
    assert r.status_code == 200, r.text
    return r.json()["data"]


def _leer(client, h, rid):
    r = client.get(f"/api/recipes/{rid}/edit", headers=h)
    assert r.status_code == 200, r.text
    return r.json()["data"]


# ── Guardar y recuperar ────────────────────────────────────────────────────

def test_SE_GUARDA_TODO_LO_CLINICO(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    h, _det, _hc = _monta(client, admin_headers, suf)
    d = _crear(client, h, f"Arroz con pollo {suf}",
               tags="Alta proteína,Meal prep",
               notes="Sustituir el arroz por quinoa si hay intolerancia",
               difficulty="media",
               allergen_free="Gluten,Lactosa",
               diet_styles="Mediterránea",
               glycemic_index="bajo", sodium_level="medio", fiber=7.5)

    leida = _leer(client, h, d["id"])
    assert leida["tags"] == "Alta proteína,Meal prep", leida["tags"]
    assert leida["notes"].startswith("Sustituir el arroz"), leida["notes"]
    assert leida["difficulty"] == "media"
    assert leida["allergen_free"] == "Gluten,Lactosa"
    assert leida["diet_styles"] == "Mediterránea"
    assert leida["glycemic_index"] == "bajo"
    assert leida["sodium_level"] == "medio"
    assert leida["fiber"] == 7.5


def test_LAS_PATOLOGIAS_SON_LAS_MISMAS_QUE_LAS_DE_LAS_DIETAS(client, seed, admin_headers):
    """Un solo catálogo: dos listas parecidas acabarían diciendo cosas
    distintas y una dieta y una receta no se podrían cruzar."""
    suf = uuid.uuid4().hex[:8]
    h, _det, _hc = _monta(client, admin_headers, suf)
    catalogo = _patologias(client, h)
    assert catalogo, "no hay catálogo de patologías"
    elegidas = [p["id"] for p in catalogo[:2]]

    d = _crear(client, h, f"Receta {suf}", pathology_ids=elegidas)
    leida = _leer(client, h, d["id"])
    assert sorted(p["id"] for p in leida["pathologies"]) == sorted(elegidas), leida["pathologies"]
    assert leida["pathologies"][0]["name"] == catalogo[0]["name"]


def test_el_catalogo_viene_agrupado(client, seed, admin_headers):
    """Una lista plana de treinta patologías no se lee: la pantalla las agrupa,
    y para eso el grupo tiene que llegar."""
    suf = uuid.uuid4().hex[:8]
    h, _det, _hc = _monta(client, admin_headers, suf)
    catalogo = _patologias(client, h)
    porNombre = {p["name"]: p.get("grupo") for p in catalogo}
    assert porNombre.get("SII / FODMAP") == "Digestivo", porNombre
    assert porNombre.get("Diabetes tipo 2") == "Metabólico", porNombre


def test_la_receta_recien_creada_ya_las_devuelve(client, seed, admin_headers):
    """La pantalla se queda con lo que responde el guardado; si viniera vacío,
    volvería a mandarlo vacío al guardar otra vez."""
    suf = uuid.uuid4().hex[:8]
    h, _det, _hc = _monta(client, admin_headers, suf)
    ids = [p["id"] for p in _patologias(client, h)[:1]]
    d = _crear(client, h, f"Receta {suf}", pathology_ids=ids, tags="Rápida")
    assert [p["id"] for p in d["pathologies"]] == ids, d["pathologies"]
    assert d["tags"] == "Rápida"


# ── Cambiar ────────────────────────────────────────────────────────────────

def test_se_pueden_cambiar_las_patologias(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    h, _det, _hc = _monta(client, admin_headers, suf)
    catalogo = _patologias(client, h)
    d = _crear(client, h, f"Receta {suf}", pathology_ids=[catalogo[0]["id"]])

    r = client.put(f"/api/recipes/{d['id']}/update", headers=h,
                   json={"pathology_ids": [catalogo[1]["id"], catalogo[2]["id"]]})
    assert r.status_code == 200, r.text
    leida = _leer(client, h, d["id"])
    assert sorted(p["id"] for p in leida["pathologies"]) == \
        sorted([catalogo[1]["id"], catalogo[2]["id"]]), leida["pathologies"]


def test_quitarlas_todas_las_quita(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    h, _det, _hc = _monta(client, admin_headers, suf)
    catalogo = _patologias(client, h)
    d = _crear(client, h, f"Receta {suf}", pathology_ids=[catalogo[0]["id"]])

    client.put(f"/api/recipes/{d['id']}/update", headers=h, json={"pathology_ids": []})
    assert _leer(client, h, d["id"])["pathologies"] == []


def test_UNA_EDICION_PARCIAL_NO_BORRA_LO_QUE_NO_TOCA(client, seed, admin_headers):
    """Cambiar solo el nombre no puede llevarse por delante las patologías ni
    las notas: es lo que hace el guardado automático de otras pantallas."""
    suf = uuid.uuid4().hex[:8]
    h, _det, _hc = _monta(client, admin_headers, suf)
    catalogo = _patologias(client, h)
    d = _crear(client, h, f"Receta {suf}", pathology_ids=[catalogo[0]["id"]],
               notes="Ojo con la sal", tags="Rápida")

    r = client.put(f"/api/recipes/{d['id']}/update", headers=h, json={"name": f"Otro nombre {suf}"})
    assert r.status_code == 200, r.text
    leida = _leer(client, h, d["id"])
    assert leida["name"] == f"Otro nombre {suf}"
    assert [p["id"] for p in leida["pathologies"]] == [catalogo[0]["id"]], leida["pathologies"]
    assert leida["notes"] == "Ojo con la sal"
    assert leida["tags"] == "Rápida"


def test_una_receta_sin_nada_clinico_no_inventa_nada(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    h, _det, _hc = _monta(client, admin_headers, suf)
    d = _crear(client, h, f"Simple {suf}")
    leida = _leer(client, h, d["id"])
    assert leida["tags"] is None and leida["notes"] is None
    assert leida["allergen_free"] is None and leida["diet_styles"] is None
    assert leida["fiber"] is None
    assert leida["pathologies"] == []


def test_las_patologias_del_catalogo_no_se_borran_con_la_receta(client, seed, admin_headers):
    """Borrar una receta no puede llevarse el catálogo por delante."""
    suf = uuid.uuid4().hex[:8]
    h, _det, _hc = _monta(client, admin_headers, suf)
    catalogo = _patologias(client, h)
    d = _crear(client, h, f"Receta {suf}", pathology_ids=[catalogo[0]["id"]])

    assert client.delete(f"/api/recipes/{d['id']}", headers=h).status_code == 200
    db = SessionLocal()
    try:
        assert db.query(Pathology).filter(Pathology.id == catalogo[0]["id"]).first() is not None
    finally:
        db.close()
