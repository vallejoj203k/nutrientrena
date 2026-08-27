"""Lo que la lista de la compra necesita del servidor: la categoría.

La lista agrupa por pasillo —"Frutas", "Aves", "Lácteos"— y esa categoría es la
del catálogo, no una inventada a partir del nombre. Sin ella, la compra sale
como una lista plana de treinta nombres y se recorre el supermercado en zigzag.

El detalle que hace que esto se pueda romper sin que nadie lo note: el alimento
que hay dentro de una dieta NO es el del catálogo, es una COPIA suya. Si la
copia no se llevara la categoría, la biblioteca del coach saldría ordenada y la
lista del cliente no — el mismo alimento, dos sitios, dos resultados.
"""
import uuid

from app.database import SessionLocal
from app.models.nutrition.aliment import Aliment
from app.models.nutrition.diet import Diet, DietFood, DietFoodAliment
from app.models.nutrition.group_food import GroupFood

from tests.test_nutricion_cliente import _asignar_directa, _monta, _nutricion


def _dieta_con(client, h_coach, titulo, alimentos):
    """`alimentos` es [(nombre, categoría|None, cantidad, unidad)]."""
    r = client.post("/api/diets", headers=h_coach, json={"title": titulo})
    assert r.status_code == 200, r.text
    did = r.json()["data"]["id"]

    db = SessionLocal()
    try:
        comida = DietFood(diet_id=did, name="Comida", time="08:00")
        db.add(comida)
        db.flush()
        for i, (nombre, categoria, cant, unidad) in enumerate(alimentos):
            gid = None
            if categoria:
                g = db.query(GroupFood).filter(GroupFood.name == categoria).first()
                if not g:
                    g = GroupFood(name=categoria)
                    db.add(g)
                    db.flush()
                gid = g.id
            al = Aliment(id=str(uuid.uuid4()), name=nombre, calories=100.0,
                         quantity=100.0, quantity_unit=unidad, group_food_id=gid)
            db.add(al)
            db.flush()
            db.add(DietFoodAliment(diet_id=did, diet_food_id=comida.id,
                                   aliment_id=al.id, quantity=cant, order=i))
        db.commit()
    finally:
        db.close()
    return did


def _alimentos(datos):
    """Los alimentos de UN día.

    Una dieta suelta se repite los siete, así que recorrer la semana entera
    devuelve siete copias de lo mismo y cualquier cuenta sale por siete.
    """
    dias = [d for d in datos["days"] if d.get("has_diet")]
    if not dias:
        return []
    return [f for m in (dias[0].get("meals") or []) for f in (m.get("foods") or [])]


def test_CADA_ALIMENTO_TRAE_SU_CATEGORIA(client, seed, admin_headers):
    """Sin esto la lista de la compra no puede agrupar por pasillo."""
    suf = uuid.uuid4().hex[:8]
    _dc, h_coach, det_cli, h_cli = _monta(client, admin_headers, suf)
    did = _dieta_con(client, h_coach, f"Plan {suf}", [
        (f"Pechuga de pollo {suf}", f"Aves {suf}", 120.0, "g"),
        (f"Manzana {suf}", f"Frutas {suf}", 1.0, "ud"),
    ])
    _asignar_directa(did, det_cli)

    por_nombre = {f["name"]: f for f in _alimentos(_nutricion(client, h_cli))}
    assert por_nombre[f"Pechuga de pollo {suf}"]["category"] == f"Aves {suf}", por_nombre
    assert por_nombre[f"Manzana {suf}"]["category"] == f"Frutas {suf}", por_nombre


def test_un_alimento_sin_categoria_no_rompe_la_respuesta(client, seed, admin_headers):
    """En el catálogo cargado no queda ninguno suelto, pero uno creado a mano
    puede no tenerla. Va como null y la pantalla lo manda a "Otros"."""
    suf = uuid.uuid4().hex[:8]
    _dc, h_coach, det_cli, h_cli = _monta(client, admin_headers, suf)
    did = _dieta_con(client, h_coach, f"Plan {suf}", [
        (f"Suelto {suf}", None, 50.0, "g")])
    _asignar_directa(did, det_cli)

    fs = _alimentos(_nutricion(client, h_cli))
    assert len(fs) == 1 and fs[0]["category"] is None, fs


def test_LA_COPIA_QUE_SE_METE_EN_LA_DIETA_CONSERVA_LA_CATEGORIA(client, seed, admin_headers):
    """El camino de verdad: el coach mete un alimento del catálogo en una dieta
    y eso crea una COPIA. Si la copia perdiera la categoría, la biblioteca
    saldría ordenada y la lista de la compra del cliente no."""
    suf = uuid.uuid4().hex[:8]
    _dc, h_coach, det_cli, h_cli = _monta(client, admin_headers, suf)

    db = SessionLocal()
    try:
        g = GroupFood(name=f"Lácteos {suf}")
        db.add(g)
        db.flush()
        original = Aliment(id=str(uuid.uuid4()), name=f"Yogur griego {suf}",
                           calories=59.0, quantity=100.0, quantity_unit="g",
                           group_food_id=g.id)
        db.add(original)
        db.commit()
        origen_id, grupo = original.id, g.name
    finally:
        db.close()

    r = client.post("/api/diets", headers=h_coach, json={"title": f"Plan {suf}"})
    did = r.json()["data"]["id"]
    r = client.put(f"/api/diets/{did}/update", headers=h_coach, json={
        "id": did, "title": f"Plan {suf}", "foods": [
            {"name": "Desayuno", "time": "08:00",
             "detail": [{"aliment_id": origen_id, "quantity_calc": 150.0, "order": 0}]}]})
    assert r.status_code == 200, r.text
    _asignar_directa(did, det_cli)

    fs = _alimentos(_nutricion(client, h_cli))
    assert len(fs) == 1, fs
    assert fs[0]["category"] == grupo, fs[0]
    # Y sigue siendo una copia, no el original: si esto dejara de ser cierto,
    # la prueba estaría comprobando otra cosa.
    db = SessionLocal()
    try:
        copia = db.query(Aliment).filter(Aliment.name == f"Yogur griego {suf}",
                                         Aliment.parent_id == origen_id).first()
        assert copia is not None, "ya no se clona: esta prueba mide otra cosa"
        assert copia.group_food_id is not None
    finally:
        db.close()
