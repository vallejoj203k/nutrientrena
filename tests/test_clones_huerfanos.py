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

Estas comprobaciones están marcadas como fallo conocido a propósito: dejan
escrito el problema y avisarán solas cuando alguien lo arregle.
"""
import uuid

import pytest

from app.database import SessionLocal
from app.models.nutrition.aliment import Aliment

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


@pytest.mark.xfail(strict=True, reason="Fallo conocido: la copia no se limpia")
def test_AL_BORRAR_LA_DIETA_SU_COPIA_TAMBIEN_SE_VA(client, seed, admin_headers):
    """La copia solo existía para esa dieta. Sin ella no le sirve a nadie: no
    sale en la biblioteca, no se puede usar, y ahí se queda contando.

    En la base del cliente esto había dejado ~7600 filas basura.
    """
    suf = uuid.uuid4().hex[:8]
    h, alid = _monta(client, admin_headers, suf)

    antes = _cuantos()
    did = _dieta_con(client, h, suf, alid)
    assert client.delete(f"/api/diets/{did}", headers=h).status_code == 200

    assert _cuantos() == antes, f"quedan {_cuantos() - antes} copias huérfanas"


@pytest.mark.xfail(strict=True, reason="Fallo conocido: la copia no se limpia")
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
