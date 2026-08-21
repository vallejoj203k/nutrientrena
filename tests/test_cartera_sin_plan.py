"""Quién está esperando su plan.

Es lo primero que mira un coach al abrir el panel, y hasta ahora la pantalla lo
adivinaba con campos que la respuesta no traía: pedía `/api/users?role_id=3`,
una ruta que no existe. Devolvía 405, la respuesta se descartaba en un `catch`
y el panel salía siempre vacío, hubiera los clientes que hubiera. Un panel que
dice "no hay nada pendiente" cuando hay veinte es peor que uno que no dice
nada.

Ahora la cartera trae `sin_plan`, `precio` y `alta`, que son los tres datos que
la tarjeta enseña: a quién le falta el plan, cuánto paga y cuánto lleva
esperando.
"""
import uuid

from app.database import SessionLocal
from app.models.nutrition.diet import Diet
from app.models.routine import Routine
from app.models.user import UserDetail, UserParent

from tests.test_org_scope import _crear_coach, _crear_usuario


def _cliente_de(client, admin_headers, coach_detail_id, email):
    _uid, det, h = _crear_usuario(client, admin_headers, email, role_id=6)
    db = SessionLocal()
    try:
        db.add(UserParent(user_detail_id=det, parent_user_detail_id=coach_detail_id))
        db.commit()
    finally:
        db.close()
    return det


def _user_id_de(detalle_id):
    db = SessionLocal()
    try:
        return db.query(UserDetail).filter(UserDetail.id == detalle_id).first().user_id
    finally:
        db.close()


def _cartera(client, headers):
    r = client.get("/api/users/clients/portfolio", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()["data"]


def _fila(datos, detalle_id):
    return next(c for c in datos["clients"] if c["id"] == detalle_id)


def test_un_cliente_recien_dado_de_alta_esta_sin_plan(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    _u, det_coach, h_coach = _crear_coach(client, admin_headers, f"coach.cart.{suf}@nutrientrena-qa.com")
    det = _cliente_de(client, admin_headers, det_coach, f"cli.cart.{suf}@nutrientrena-qa.com")

    f = _fila(_cartera(client, h_coach), det)
    assert f["sin_plan"] is True, f
    assert f["tiene_dieta"] is False and f["tiene_rutina"] is False, f
    # Sin esto no se puede decir "Alta hace 3 días", que es lo que ordena la lista.
    assert f["alta"], f


def test_con_una_dieta_ya_no_esta_sin_plan(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    _u, det_coach, h_coach = _crear_coach(client, admin_headers, f"coach.cart.{suf}@nutrientrena-qa.com")
    det = _cliente_de(client, admin_headers, det_coach, f"cli.cart.{suf}@nutrientrena-qa.com")

    db = SessionLocal()
    try:
        db.add(Diet(id=str(uuid.uuid4()), title=f"Dieta {suf}", user_id=_user_id_de(det)))
        db.commit()
    finally:
        db.close()

    f = _fila(_cartera(client, h_coach), det)
    assert f["tiene_dieta"] is True and f["sin_plan"] is False, f


def test_con_solo_una_rutina_tampoco(client, seed, admin_headers):
    """Cuenta cualquiera de las dos: hay coaches que solo entrenan y hay
    nutricionistas que solo pautan comida."""
    suf = uuid.uuid4().hex[:8]
    _u, det_coach, h_coach = _crear_coach(client, admin_headers, f"coach.cart.{suf}@nutrientrena-qa.com")
    det = _cliente_de(client, admin_headers, det_coach, f"cli.cart.{suf}@nutrientrena-qa.com")

    db = SessionLocal()
    try:
        db.add(Routine(name=f"Rutina {suf}", user_id=_user_id_de(det)))
        db.commit()
    finally:
        db.close()

    f = _fila(_cartera(client, h_coach), det)
    assert f["tiene_rutina"] is True and f["sin_plan"] is False, f


def test_el_precio_sale_en_la_cartera(client, seed, admin_headers):
    """La tarjeta enseña «250€/mes»: dice a quién atender primero."""
    suf = uuid.uuid4().hex[:8]
    _u, det_coach, h_coach = _crear_coach(client, admin_headers, f"coach.cart.{suf}@nutrientrena-qa.com")
    det = _cliente_de(client, admin_headers, det_coach, f"cli.cart.{suf}@nutrientrena-qa.com")

    db = SessionLocal()
    try:
        d = db.query(UserDetail).filter(UserDetail.id == det).first()
        d.precio = 250.0
        db.commit()
    finally:
        db.close()

    assert _fila(_cartera(client, h_coach), det)["precio"] == 250.0


def test_el_recuento_de_sin_plan_cuadra_con_la_lista(client, seed, admin_headers):
    """El número grande del indicador y la lista de debajo salen del mismo
    sitio: si no cuadran, una de las dos miente y no se sabe cuál."""
    suf = uuid.uuid4().hex[:8]
    _u, det_coach, h_coach = _crear_coach(client, admin_headers, f"coach.cart.{suf}@nutrientrena-qa.com")
    for n in range(3):
        _cliente_de(client, admin_headers, det_coach, f"cli{n}.cart.{suf}@nutrientrena-qa.com")

    datos = _cartera(client, h_coach)
    de_la_lista = [c for c in datos["clients"]
                   if c["sin_plan"] and c["lifecycle_status"] == "activo"]
    assert datos["stats"]["sin_plan"] == len(de_la_lista) == 3, datos["stats"]


def test_un_coach_no_ve_los_clientes_de_otro(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    _uA, detA, h_coachA = _crear_coach(client, admin_headers, f"coachA.cart.{suf}@nutrientrena-qa.com")
    _uB, detB, h_coachB = _crear_coach(client, admin_headers, f"coachB.cart.{suf}@nutrientrena-qa.com")
    _cliente_de(client, admin_headers, detA, f"cliA.cart.{suf}@nutrientrena-qa.com")
    ajeno = _cliente_de(client, admin_headers, detB, f"cliB.cart.{suf}@nutrientrena-qa.com")

    ids = {c["id"] for c in _cartera(client, h_coachA)["clients"]}
    assert ajeno not in ids


def test_un_coach_sin_clientes_no_da_error(client, seed, admin_headers):
    """La pantalla tiene que poder pintarse igual el primer día."""
    suf = uuid.uuid4().hex[:8]
    _u, _det, h_coach = _crear_coach(client, admin_headers, f"coach.vacio.{suf}@nutrientrena-qa.com")
    datos = _cartera(client, h_coach)
    assert datos["clients"] == [] and datos["stats"]["sin_plan"] == 0, datos
