"""La receta dice QUÉ ingrediente lleva, no solo a qué id apunta.

`details` traía `aliment_id` y nada más. El panel de detalle ponía
"Ingrediente · 200g" en todas las líneas, y el editor tenía que pedir los
alimentos uno a uno para recuperar los nombres: con diez ingredientes, diez
peticiones, y cualquiera que fallara dejaba una fila sin nombre y sin macros,
contando como cero en el total de la receta.

Lo que hay que dejar sujeto:

  · Que el alimento venga con el ingrediente, al abrir la receta y al listarla.
  · Con lo que hace falta para pintar la línea: nombre, cantidad y unidad.
  · Y que un ingrediente cuyo alimento ya no existe no reviente la receta.
"""
import uuid

from app.database import SessionLocal
from app.models.nutrition.recipe import Recipe, RecipeDetail

from tests.test_macros_porcion import _monta


def _alimento(client, h, nombre, **campos):
    body = {"name": nombre, "calories": 165, "proteins": 31, "carbohydrates": 0,
            "fats": 3.6, "quantity": 100, "quantity_unit": "g"}
    body.update(campos)
    r = client.post("/api/aliments", headers=h, json=body)
    assert r.status_code == 200, r.text
    return r.json()["data"]["id"]


def _receta(client, h, nombre, detalles):
    r = client.post("/api/recipes", headers=h, json={
        "name": nombre, "instructions": "Cuece el arroz\nDora el pollo",
        "servings": 2, "prep_time": 30, "details": detalles})
    assert r.status_code == 200, r.text
    return r.json()["data"]["id"]


def test_EL_INGREDIENTE_TRAE_SU_ALIMENTO(client, seed, admin_headers):
    """El caso reportado: todas las líneas decían "Ingrediente"."""
    suf = uuid.uuid4().hex[:8]
    h, _det, _hc = _monta(client, admin_headers, suf)
    pollo = _alimento(client, h, f"Pechuga de pollo {suf}")
    rid = _receta(client, h, f"Arroz con pollo {suf}",
                  [{"aliment_id": pollo, "quantity": 250, "order": 0}])

    d = client.get(f"/api/recipes/{rid}/edit", headers=h).json()["data"]
    ing = d["details"][0]
    assert ing.get("aliment"), "el ingrediente no trae su alimento"
    assert ing["aliment"]["name"] == f"Pechuga de pollo {suf}", ing["aliment"]
    assert ing["quantity"] == 250


def test_trae_lo_que_hace_falta_para_pintar_la_linea(client, seed, admin_headers):
    """Nombre y unidad: sin la unidad, un huevo sale como "1 g"."""
    suf = uuid.uuid4().hex[:8]
    h, _det, _hc = _monta(client, admin_headers, suf)
    huevo = _alimento(client, h, f"Huevo {suf}", quantity=1, quantity_unit="ud", calories=74)
    rid = _receta(client, h, f"Tortilla {suf}",
                  [{"aliment_id": huevo, "quantity": 2, "order": 0}])

    al = client.get(f"/api/recipes/{rid}/edit", headers=h).json()["data"]["details"][0]["aliment"]
    assert al["quantity_unit"] == "ud", al
    assert al["quantity"] == 1, al
    assert al["calories"] == 74, al


def test_y_la_preparacion_viaja_con_la_receta(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    h, _det, _hc = _monta(client, admin_headers, suf)
    pollo = _alimento(client, h, f"Pollo {suf}")
    rid = _receta(client, h, f"Receta {suf}", [{"aliment_id": pollo, "quantity": 100, "order": 0}])

    d = client.get(f"/api/recipes/{rid}/edit", headers=h).json()["data"]
    assert d["instructions"] == "Cuece el arroz\nDora el pollo", d["instructions"]


def test_la_lista_tambien_los_trae(client, seed, admin_headers):
    """El panel se abre desde la lista, sin volver a pedir la receta."""
    suf = uuid.uuid4().hex[:8]
    h, _det, _hc = _monta(client, admin_headers, suf)
    pollo = _alimento(client, h, f"Pechuga {suf}")
    rid = _receta(client, h, f"Arroz {suf}", [{"aliment_id": pollo, "quantity": 250, "order": 0}])

    r = client.get(f"/api/recipes/search?search=Arroz {suf}", headers=h)
    assert r.status_code == 200, r.text
    mias = [x for x in r.json()["data"]["data"] if x["id"] == rid]
    assert mias, "no sale en la búsqueda"
    assert mias[0]["details"][0]["aliment"]["name"] == f"Pechuga {suf}", mias[0]["details"]


def test_UN_ALIMENTO_QUE_YA_NO_ESTA_NO_REVIENTA_LA_RECETA(client, seed, admin_headers):
    """Queda la línea, sin alimento, y la pantalla lo dice. Antes o después
    pasa: alguien borra del catálogo algo que estaba en una receta."""
    suf = uuid.uuid4().hex[:8]
    h, _det, _hc = _monta(client, admin_headers, suf)
    pollo = _alimento(client, h, f"Pollo {suf}")
    rid = _receta(client, h, f"Receta {suf}", [{"aliment_id": pollo, "quantity": 100, "order": 0}])

    db = SessionLocal()
    try:
        # Un id que no existe, como queda una receta cuyo alimento se borró.
        det = db.query(RecipeDetail).filter(RecipeDetail.recipe_id == rid).first()
        det.aliment_id = str(uuid.uuid4())
        db.commit()
    finally:
        db.close()

    r = client.get(f"/api/recipes/{rid}/edit", headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["data"]["details"][0]["aliment"] is None


def test_una_receta_sin_ingredientes_sale_igual(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    h, _det, _hc = _monta(client, admin_headers, suf)
    rid = _receta(client, h, f"Vacía {suf}", [])

    d = client.get(f"/api/recipes/{rid}/edit", headers=h).json()["data"]
    assert d["details"] == [], d["details"]


def test_no_se_pide_un_alimento_por_ingrediente(client, seed, admin_headers):
    """Diez ingredientes eran diez peticiones más. Se comprueba que la receta
    llega entera de una vez, con los diez nombres puestos."""
    suf = uuid.uuid4().hex[:8]
    h, _det, _hc = _monta(client, admin_headers, suf)
    detalles = [{"aliment_id": _alimento(client, h, f"Alimento {i} {suf}"),
                 "quantity": 100, "order": i} for i in range(10)]
    rid = _receta(client, h, f"Larga {suf}", detalles)

    d = client.get(f"/api/recipes/{rid}/edit", headers=h).json()["data"]
    nombres = [x["aliment"]["name"] for x in d["details"] if x.get("aliment")]
    assert len(nombres) == 10, nombres
