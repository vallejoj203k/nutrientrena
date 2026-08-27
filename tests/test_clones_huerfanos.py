"""Los clones de alimentos que se quedan huérfanos.

Cada vez que se mete un alimento en una dieta NO se apunta al alimento del
catálogo: se hace una COPIA suya (con `parent_id` apuntando al original) y la
dieta apunta a la copia. Tiene sentido — así editar la dieta de un cliente no
le cambia las kcal a la biblioteca ni a los demás clientes.

Lo que falta es la limpieza. Cuando esa copia deja de usarse —se quita el
alimento de la comida, se borra la comida, se borra la dieta entera— la fila
del alimento se queda en la tabla para siempre. Nadie la ve en la biblioteca
(no sale en los listados) pero ahí está, ocupando y contando.

Se descubrió al preparar la carga del catálogo nuevo: la base del cliente tenía
7762 alimentos y solo 107 filas de `diet_food_aliments`. Los otros ~7600 eran
esto.

Arreglado: ahora, cuando una copia deja de usarse, se recoge. Solo se borra lo
que es una copia Y no lo usa ninguna dieta, ninguna receta y no es padre de otra
copia — un alimento del catálogo no se toca jamás por aquí, aunque nadie lo esté
usando.
"""
import uuid

from app.database import SessionLocal
from app.models.nutrition.aliment import Aliment
from app.models.nutrition.diet import DietFoodAliment

from tests.test_org_scope import _crear_coach


def _cuantos():
    db = SessionLocal()
    try:
        return db.query(Aliment).count()
    finally:
        db.close()


def _monta(client, admin_headers, suf):
    _u, _d, h = _crear_coach(client, admin_headers, f"coach.clon.{suf}@nutrientrena-qa.com")
    db = SessionLocal()
    try:
        al = Aliment(id=str(uuid.uuid4()), name=f"Pollo {suf}", calories=165.0,
                     quantity=100.0, quantity_unit="g")
        db.add(al)
        db.commit()
        return h, al.id
    finally:
        db.close()


def _dieta_con(client, h, suf, alid):
    r = client.post("/api/diets", headers=h, json={
        "title": f"Dieta {suf}",
        "foods": [{"name": "Comida", "detail": [
            {"aliment_id": alid, "quantity_calc": 100, "order": 0}]}]})
    assert r.status_code == 200, r.text
    return r.json()["data"]["id"]


def test_meter_un_alimento_en_una_dieta_hace_una_copia(client, seed, admin_headers):
    """Esto es a propósito y está bien: editar la dieta de un cliente no puede
    cambiarle las kcal a la biblioteca ni a los demás clientes."""
    suf = uuid.uuid4().hex[:8]
    h, alid = _monta(client, admin_headers, suf)

    antes = _cuantos()
    _dieta_con(client, h, suf, alid)
    assert _cuantos() == antes + 1, "no se ha hecho la copia"

    db = SessionLocal()
    try:
        copia = db.query(Aliment).filter(Aliment.parent_id == alid).first()
        assert copia is not None, "la copia no apunta a su original"
    finally:
        db.close()


def test_AL_BORRAR_LA_DIETA_SU_COPIA_TAMBIEN_SE_VA(client, seed, admin_headers):
    """La copia solo existía para esa dieta. Sin ella no le sirve a nadie: no
    sale en la biblioteca, no se puede usar, y ahí se queda contando.

    En la base del cliente esto había dejado miles de filas basura.
    """
    suf = uuid.uuid4().hex[:8]
    h, alid = _monta(client, admin_headers, suf)

    antes = _cuantos()
    did = _dieta_con(client, h, suf, alid)
    assert client.delete(f"/api/diets/{did}", headers=h).status_code == 200

    assert _cuantos() == antes, f"quedan {_cuantos() - antes} copias huérfanas"


def test_y_al_quitar_el_alimento_de_la_comida_tambien(client, seed, admin_headers):
    """Editar una dieta quitando un alimento deja su copia suelta. Con un coach
    retocando dietas a diario, esto crece sin techo."""
    suf = uuid.uuid4().hex[:8]
    h, alid = _monta(client, admin_headers, suf)

    antes = _cuantos()
    did = _dieta_con(client, h, suf, alid)
    comida = client.get(f"/api/diets/{did}/edit", headers=h).json()["data"]["foods"][0]
    client.put(f"/api/diets/{did}/update", headers=h, json={
        "id": did, "title": f"Dieta {suf}",
        "foods": [{"id": comida["id"], "name": "Comida", "detail": []}]})

    assert _cuantos() == antes, f"quedan {_cuantos() - antes} copias huérfanas"


# ── Lo que NO se puede llevar por delante ──────────────────────────────────
#
# Una limpieza que borra de más es peor que la fuga: la fuga solo ocupa sitio,
# esto se lleva el catálogo del que cuelgan las dietas de todo el mundo.

def test_EL_ALIMENTO_DEL_CATALOGO_NO_SE_TOCA_NUNCA(client, seed, admin_headers):
    """Aunque no lo use nadie. Un alimento de la biblioteca está ahí para que
    los coaches lo encuentren, no porque alguien lo esté usando ahora.

    Se monta a mano una dieta que apunta DIRECTAMENTE al alimento del catálogo,
    sin copia de por medio. Pasa con datos viejos, de antes de que se clonara.
    Sin montarlo así la comprobación no vale: por el camino normal el original
    nunca llega a estar entre los candidatos a borrar, así que quitar la guarda
    no rompería nada y esto pasaría igual. Lo comprobé quitándola.
    """
    suf = uuid.uuid4().hex[:8]
    h, alid = _monta(client, admin_headers, suf)

    from app.models.nutrition.diet import Diet, DietFood
    db = SessionLocal()
    try:
        d = Diet(id=str(uuid.uuid4()), title=f"Dieta vieja {suf}")
        db.add(d)
        db.flush()
        f = DietFood(diet_id=d.id, name="Comida")
        db.add(f)
        db.flush()
        db.add(DietFoodAliment(diet_id=d.id, diet_food_id=f.id,
                               aliment_id=alid, quantity=100.0, order=0))
        db.commit()
        did = d.id
    finally:
        db.close()

    # Como admin: la dieta se montó a mano y no tiene dueño, así que al coach
    # se le bloquea por no ser suya — que es otra comprobación, no esta.
    assert client.delete(f"/api/diets/{did}", headers=admin_headers).status_code == 200

    db = SessionLocal()
    try:
        original = db.query(Aliment).filter(Aliment.id == alid).first()
        assert original is not None, "se ha borrado el alimento del CATÁLOGO"
        assert original.name == f"Pollo {suf}"
    finally:
        db.close()


def test_UNA_COPIA_QUE_OTRA_DIETA_SIGUE_USANDO_SE_QUEDA(client, seed, admin_headers):
    """Dos dietas apuntando a la MISMA copia: borrar una no puede dejar a la
    otra sin su alimento.

    Se monta a mano porque por el camino normal cada dieta hace su propia
    copia y nunca se comparte una. Sin compartirla, quitar la comprobación de
    "¿lo usa alguien más?" no rompería nada y esto pasaría igual — lo comprobé
    quitándola.
    """
    suf = uuid.uuid4().hex[:8]
    h, alid = _monta(client, admin_headers, suf)
    d1 = _dieta_con(client, h, suf, alid)

    from app.models.nutrition.diet import Diet, DietFood
    db = SessionLocal()
    try:
        copia = db.query(DietFoodAliment.aliment_id).filter(
            DietFoodAliment.diet_id == d1).first()[0]
        # Otra dieta apuntando a esa MISMA copia.
        d = Diet(id=str(uuid.uuid4()), title=f"La otra {suf}")
        db.add(d)
        db.flush()
        f = DietFood(diet_id=d.id, name="Comida")
        db.add(f)
        db.flush()
        db.add(DietFoodAliment(diet_id=d.id, diet_food_id=f.id,
                               aliment_id=copia, quantity=100.0, order=0))
        db.commit()
        d2 = d.id
    finally:
        db.close()

    assert client.delete(f"/api/diets/{d1}", headers=h).status_code == 200

    db = SessionLocal()
    try:
        assert db.query(Aliment).filter(Aliment.id == copia).first() is not None, \
            "la otra dieta se ha quedado sin su alimento"
        assert db.query(DietFoodAliment).filter(
            DietFoodAliment.diet_id == d2).count() == 1
    finally:
        db.close()


def test_QUITAR_UN_ALIMENTO_Y_PONER_OTRO_EN_LA_MISMA_EDICION(client, seed, admin_headers):
    """Se recoge al FINAL de guardar, no sobre la marcha. Si se limpiara según
    se quita, un alimento movido de una comida a otra dentro del mismo guardado
    se borraría justo después de haberlo puesto donde toca."""
    suf = uuid.uuid4().hex[:8]
    h, alid = _monta(client, admin_headers, suf)
    did = _dieta_con(client, h, suf, alid)

    detalle = client.get(f"/api/diets/{did}/edit", headers=h).json()["data"]
    comida = detalle["foods"][0]
    dfa = comida["detail"][0]

    # Se quita de esa comida y se pone en una nueva, en la misma petición.
    r = client.put(f"/api/diets/{did}/update", headers=h, json={
        "id": did, "title": f"Dieta {suf}",
        "foods": [
            {"id": comida["id"], "name": "Comida", "detail": []},
            {"name": "Otra comida", "detail": [
                {"aliment_id": dfa["aliment_id"], "quantity_calc": 50, "order": 0}]},
        ]})
    assert r.status_code == 200, r.text

    de_nuevo = client.get(f"/api/diets/{did}/edit", headers=h).json()["data"]
    con_alimentos = [f for f in de_nuevo["foods"] if f["detail"]]
    assert len(con_alimentos) == 1, de_nuevo["foods"]
    assert con_alimentos[0]["detail"][0]["quantity"] == 50


def test_cambiar_el_alimento_de_una_fila_recoge_el_anterior(client, seed, admin_headers):
    """Al cambiar de alimento se hace una copia nueva y la vieja se queda
    suelta. Es el caso que más se repite: un coach ajustando una dieta."""
    suf = uuid.uuid4().hex[:8]
    h, alid = _monta(client, admin_headers, suf)
    db = SessionLocal()
    try:
        otro = Aliment(id=str(uuid.uuid4()), name=f"Ternera {suf}", calories=250.0,
                       quantity=100.0, quantity_unit="g")
        db.add(otro)
        db.commit()
        otro_id = otro.id
    finally:
        db.close()

    antes = _cuantos()
    did = _dieta_con(client, h, suf, alid)
    detalle = client.get(f"/api/diets/{did}/edit", headers=h).json()["data"]
    comida = detalle["foods"][0]
    dfa = comida["detail"][0]

    client.put(f"/api/diets/{did}/update", headers=h, json={
        "id": did, "title": f"Dieta {suf}",
        "foods": [{"id": comida["id"], "name": "Comida", "detail": [
            {"id": dfa["id"], "aliment_id": otro_id, "quantity_calc": 100, "order": 0}]}]})

    # Los dos del catálogo + UNA copia, la del alimento nuevo.
    assert _cuantos() == antes + 1, f"quedan {_cuantos() - antes - 1} copias de más"
