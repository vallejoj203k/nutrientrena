"""Repartir por días las dietas que el cliente ya tiene.

Asignar tres dietas a un cliente no reparte nada: las tres valen para los siete
días y el cliente acaba viendo sólo una. Era lo reportado —«aparece repetido el
mismo menú»—. `PUT /weekly-menus/client/{id}` dice qué dieta come cada día.

Se separa a propósito de `POST /weekly-menus/{id}/assign`, que parte de una
plantilla de la biblioteca y COPIA sus dietas al cliente. Aquí las dietas ya son
del cliente, así que copiarlas otra vez le dejaría cada una repetida. Eso es lo
que comprueba `test_repartir_NO_duplica_las_dietas_del_cliente`.
"""
import uuid

from app.database import SessionLocal
from app.models.client_menu import ClientMenu
from app.models.nutrition.diet import Diet
from app.models.weekly_menu import WeeklyMenu, WeeklyMenuDay

from tests.test_nutricion_cliente import _asignar_directa, _dieta_con_comida, _monta

DIAS = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']


def _semana(ids):
    """Los siete días, cada uno con la dieta que le toca (o None)."""
    return {"days": [{"day_index": i, "name": DIAS[i], "diet_id": ids[i]} for i in range(7)]}


def _tres_dietas(client, h_coach, det_cli, suf):
    ids = []
    for n in ('A', 'B', 'C'):
        did = _dieta_con_comida(client, h_coach, f"Dieta {n} {suf}", 2000)
        _asignar_directa(did, det_cli)
        ids.append(did)
    return ids


def _comidas_por_dia(client, h_cli):
    r = client.get("/api/client/nutrition", headers=h_cli)
    assert r.status_code == 200, r.text
    d = r.json()["data"]
    return d, [((x.get("meals") or [{}])[0].get("name") if x.get("meals") else None)
               for x in d["days"]]


# ── Lo que se pidió: decir qué come cada día ────────────────────────────────

def test_REPARTIR_LAS_DIETAS_HACE_QUE_CADA_DIA_SEA_DISTINTO(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    _dc, h_coach, det_cli, h_cli = _monta(client, admin_headers, suf)
    a, b, c = _tres_dietas(client, h_coach, det_cli, suf)

    # Sin repartir: los siete días traen lo mismo. Es el fallo reportado.
    datos, antes = _comidas_por_dia(client, h_cli)
    assert datos["plan_semanal"] is False, datos
    assert len(set(antes)) == 1, antes

    # En ciclo, como propone la pantalla: A B C A B C A
    r = client.put(f"/api/weekly-menus/client/{det_cli}", headers=h_coach,
                   json=_semana([a, b, c, a, b, c, a]))
    assert r.status_code == 200, r.text

    datos, despues = _comidas_por_dia(client, h_cli)
    assert datos["plan_semanal"] is True, datos
    assert len({despues[0], despues[1], despues[2]}) == 3, despues
    assert despues[3] == despues[0], despues     # el ciclo vuelve a empezar
    assert despues[6] == despues[0], despues


def test_un_dia_puede_quedarse_sin_dieta(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    _dc, h_coach, det_cli, h_cli = _monta(client, admin_headers, suf)
    a, b, _c = _tres_dietas(client, h_coach, det_cli, suf)

    r = client.put(f"/api/weekly-menus/client/{det_cli}", headers=h_coach,
                   json=_semana([a, b, a, b, a, None, None]))
    assert r.status_code == 200, r.text

    _d, comidas = _comidas_por_dia(client, h_cli)
    assert comidas[5] is None and comidas[6] is None, comidas
    assert comidas[0] is not None, comidas


def test_repartir_NO_duplica_las_dietas_del_cliente(client, seed, admin_headers):
    """El motivo de no reutilizar `POST /{id}/assign`, que sí copia.

    Si esto copiara, el coach abriría la ficha y vería cada dieta dos veces sin
    haber hecho nada.
    """
    suf = uuid.uuid4().hex[:8]
    _dc, h_coach, det_cli, _hcli = _monta(client, admin_headers, suf)
    a, b, c = _tres_dietas(client, h_coach, det_cli, suf)

    db = SessionLocal()
    try:
        from app.models.user import UserDetail
        uid = db.query(UserDetail).filter(UserDetail.id == det_cli).first().user_id
        antes = db.query(Diet).filter(Diet.user_id == uid).count()
    finally:
        db.close()

    client.put(f"/api/weekly-menus/client/{det_cli}", headers=h_coach,
               json=_semana([a, b, c, a, b, c, a]))

    db = SessionLocal()
    try:
        despues = db.query(Diet).filter(Diet.user_id == uid).count()
    finally:
        db.close()
    assert despues == antes == 3, (antes, despues)


def test_volver_a_guardar_reescribe_la_semana_y_no_la_acumula(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    _dc, h_coach, det_cli, h_cli = _monta(client, admin_headers, suf)
    a, b, c = _tres_dietas(client, h_coach, det_cli, suf)

    client.put(f"/api/weekly-menus/client/{det_cli}", headers=h_coach,
               json=_semana([a, a, a, a, a, a, a]))
    r = client.put(f"/api/weekly-menus/client/{det_cli}", headers=h_coach,
                   json=_semana([c, c, c, c, c, c, c]))
    assert r.status_code == 200, r.text
    assert len(r.json()["data"]["days"]) == 7, r.json()["data"]["days"]

    db = SessionLocal()
    try:
        cm = db.query(ClientMenu).filter(ClientMenu.client_user_detail_id == det_cli).all()
        assert len(cm) == 1, cm      # un solo menú vigente, no uno por guardado
        filas = db.query(WeeklyMenuDay).filter(WeeklyMenuDay.menu_id == cm[0].menu_id).count()
        assert filas == 7, filas
    finally:
        db.close()

    _d, comidas = _comidas_por_dia(client, h_cli)
    assert len(set(comidas)) == 1, comidas
    assert b not in [x for x in comidas], comidas


# ── Lo que no se puede guardar ──────────────────────────────────────────────

def test_media_semana_no_se_guarda(client, seed, admin_headers):
    """Guardar cuatro días dejaría los otros tres con lo que hubiera antes, y el
    coach no tendría forma de saber qué come su cliente el resto de días."""
    suf = uuid.uuid4().hex[:8]
    _dc, h_coach, det_cli, _hcli = _monta(client, admin_headers, suf)
    a, _b, _c = _tres_dietas(client, h_coach, det_cli, suf)

    r = client.put(f"/api/weekly-menus/client/{det_cli}", headers=h_coach, json={
        "days": [{"day_index": i, "name": DIAS[i], "diet_id": a} for i in range(4)]})
    assert r.status_code == 422, r.text

    db = SessionLocal()
    try:
        assert db.query(ClientMenu).filter(
            ClientMenu.client_user_detail_id == det_cli).count() == 0
    finally:
        db.close()


def test_un_dia_repetido_tampoco(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    _dc, h_coach, det_cli, _hcli = _monta(client, admin_headers, suf)
    a, _b, _c = _tres_dietas(client, h_coach, det_cli, suf)

    dias = [{"day_index": i, "name": DIAS[i], "diet_id": a} for i in range(6)]
    dias.append({"day_index": 0, "name": "Lunes otra vez", "diet_id": a})
    r = client.put(f"/api/weekly-menus/client/{det_cli}", headers=h_coach, json={"days": dias})
    assert r.status_code == 422, r.text


def test_NO_SE_PUEDE_APUNTAR_A_LA_DIETA_DE_OTRO_CLIENTE(client, seed, admin_headers):
    """Si no se comprobara, un cliente vería en su panel la comida de otro."""
    suf = uuid.uuid4().hex[:8]
    _dc, h_coach, det_cli, _hcli = _monta(client, admin_headers, suf)
    mia, _b, _c = _tres_dietas(client, h_coach, det_cli, suf)

    _dc2, h_coach2, det_otro, _h2 = _monta(client, admin_headers, uuid.uuid4().hex[:8])
    ajena = _dieta_con_comida(client, h_coach2, f"Dieta ajena {suf}", 1500)
    _asignar_directa(ajena, det_otro)

    r = client.put(f"/api/weekly-menus/client/{det_cli}", headers=h_coach,
                   json=_semana([mia, ajena, mia, mia, mia, mia, mia]))
    assert r.status_code == 422, r.text

    db = SessionLocal()
    try:
        assert db.query(ClientMenu).filter(
            ClientMenu.client_user_detail_id == det_cli).count() == 0
    finally:
        db.close()


def test_una_dieta_de_la_biblioteca_sin_asignar_tampoco_vale(client, seed, admin_headers):
    """La plantilla de la biblioteca no es del cliente: si se pudiera apuntar a
    ella, editarla le cambiaría la comida a todos sus clientes a la vez."""
    suf = uuid.uuid4().hex[:8]
    _dc, h_coach, det_cli, _hcli = _monta(client, admin_headers, suf)
    mia, _b, _c = _tres_dietas(client, h_coach, det_cli, suf)
    plantilla = _dieta_con_comida(client, h_coach, f"Plantilla {suf}", 1800)

    r = client.put(f"/api/weekly-menus/client/{det_cli}", headers=h_coach,
                   json=_semana([mia, plantilla, mia, mia, mia, mia, mia]))
    assert r.status_code == 422, r.text


# ── Repartir solo al asignar, desde CUALQUIER sitio ─────────────────────────
#
# Lo anterior arreglaba la ficha del cliente. Pero las dietas también se
# asignan desde la biblioteca (diets.html), una a una, y por ahí el cliente
# seguía viendo la misma dieta todos los días — que es justo lo que se volvió a
# reportar. Por eso el reparto se hace en la asignación, no en la pantalla.

def _asignar_por_api(client, h_coach, diet_id, det_cli):
    r = client.post(f"/api/diets/{diet_id}/assign", headers=h_coach,
                    json={"client_id": det_cli})
    assert r.status_code == 200, r.text
    return r.json()


def test_ASIGNAR_LA_SEGUNDA_DIETA_YA_REPARTE_LA_SEMANA(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    _dc, h_coach, det_cli, h_cli = _monta(client, admin_headers, suf)
    a = _dieta_con_comida(client, h_coach, f"Uno {suf}", 1000)
    b = _dieta_con_comida(client, h_coach, f"Dos {suf}", 2000)

    # Con una sola dieta no hay nada que repartir: vale para toda la semana.
    _asignar_por_api(client, h_coach, a, det_cli)
    datos, comidas = _comidas_por_dia(client, h_cli)
    assert datos["plan_semanal"] is False, datos
    assert len(set(comidas)) == 1, comidas

    # Con la segunda, sí.
    j = _asignar_por_api(client, h_coach, b, det_cli)
    assert "repartida" in j["message"].lower(), j["message"]
    datos, comidas = _comidas_por_dia(client, h_cli)
    assert datos["plan_semanal"] is True, datos
    assert comidas[0] != comidas[1], comidas
    assert comidas[2] == comidas[0], comidas       # el ciclo vuelve a empezar


def test_la_tercera_dieta_ENTRA_en_el_reparto_y_no_se_queda_fuera(client, seed, admin_headers):
    """El caso de la pantalla, que asigna varias seguidas.

    Si el reparto sólo se hiciera la primera vez, la tercera dieta no comería
    ningún día y el coach la vería asignada sin que su cliente la probara nunca.
    """
    suf = uuid.uuid4().hex[:8]
    _dc, h_coach, det_cli, h_cli = _monta(client, admin_headers, suf)
    for n in ('Uno', 'Dos', 'Tres'):
        _asignar_por_api(
            client, h_coach, _dieta_con_comida(client, h_coach, f"{n} {suf}", 2000), det_cli)

    _datos, comidas = _comidas_por_dia(client, h_cli)
    assert len(set(comidas[:3])) == 3, comidas
    assert comidas[3] == comidas[0], comidas


def test_NO_PISA_EL_REPARTO_QUE_EL_COACH_HIZO_A_MANO(client, seed, admin_headers):
    """Lo que decide el coach manda. Si asignar una dieta más rehiciera el
    ciclo, le desharía el reparto sin avisar."""
    suf = uuid.uuid4().hex[:8]
    _dc, h_coach, det_cli, h_cli = _monta(client, admin_headers, suf)
    a = _dieta_con_comida(client, h_coach, f"Uno {suf}", 1000)
    b = _dieta_con_comida(client, h_coach, f"Dos {suf}", 2000)
    _asignar_por_api(client, h_coach, a, det_cli)
    _asignar_por_api(client, h_coach, b, det_cli)

    # El coach lo cambia: todo el fin de semana libre.
    r = client.get(f"/api/diets/client/{det_cli}", headers=h_coach)
    copias = [d["id"] for g in r.json()["data"] for d in (g.get("diets") or [g]) if d.get("id")]
    assert len(copias) == 2, copias
    a_mano = [copias[0]] * 5 + [None, None]
    assert client.put(f"/api/weekly-menus/client/{det_cli}", headers=h_coach,
                      json=_semana(a_mano)).status_code == 200

    # Y ahora asigna una tercera.
    j = _asignar_por_api(
        client, h_coach, _dieta_con_comida(client, h_coach, f"Tres {suf}", 3000), det_cli)
    assert "repartida" not in j["message"].lower(), j["message"]

    _datos, comidas = _comidas_por_dia(client, h_cli)
    assert comidas[5] is None and comidas[6] is None, comidas
    assert len(set(comidas[:5])) == 1, comidas


def test_tampoco_pisa_un_menu_semanal_asignado_de_la_biblioteca(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    _dc, h_coach, det_cli, h_cli = _monta(client, admin_headers, suf)
    d1 = _dieta_con_comida(client, h_coach, f"Menu lunes {suf}", 1000)
    menu = client.post("/api/weekly-menus", headers=h_coach, json={
        "name": f"Semana {suf}",
        "days": [{"day_index": i, "name": DIAS[i], "diet_id": d1 if i < 2 else None}
                 for i in range(7)]})
    assert client.post(f"/api/weekly-menus/{menu.json()['data']['id']}/assign",
                       headers=h_coach, json={"client_id": det_cli}).status_code == 200

    _asignar_por_api(
        client, h_coach, _dieta_con_comida(client, h_coach, f"Suelta {suf}", 2000), det_cli)

    _datos, comidas = _comidas_por_dia(client, h_cli)
    assert comidas[0] is not None and comidas[1] is not None, comidas
    assert all(c is None for c in comidas[2:]), comidas


# ── Que no se pise el menú de otro cliente ──────────────────────────────────

def test_no_reescribe_un_menu_que_comparte_otro_cliente(client, seed, admin_headers):
    """Dos clientes pueden acabar apuntando al mismo menú. Repartir la semana de
    uno no puede cambiarle la comida al otro sin avisar: se le hace uno propio.
    """
    suf = uuid.uuid4().hex[:8]
    _dc, h_coach, det_cli, _hcli = _monta(client, admin_headers, suf)
    a, b, _c = _tres_dietas(client, h_coach, det_cli, suf)
    _dc2, _hc2, det_otro, _h2 = _monta(client, admin_headers, uuid.uuid4().hex[:8])

    db = SessionLocal()
    try:
        compartido = WeeklyMenu(name=f"Compartido {suf}", coach_id=1)
        db.add(compartido)
        db.flush()
        for i in range(7):
            db.add(WeeklyMenuDay(menu_id=compartido.id, day_index=i, name=DIAS[i], diet_id=a))
        db.add(ClientMenu(client_user_detail_id=det_cli, menu_id=compartido.id))
        db.add(ClientMenu(client_user_detail_id=det_otro, menu_id=compartido.id))
        db.commit()
        mid = compartido.id
    finally:
        db.close()

    r = client.put(f"/api/weekly-menus/client/{det_cli}", headers=h_coach,
                   json=_semana([b] * 7))
    assert r.status_code == 200, r.text
    assert r.json()["data"]["id"] != mid, "se ha reescrito el menú compartido"

    db = SessionLocal()
    try:
        # El menú compartido sigue como estaba, con la dieta A todos los días.
        dias = db.query(WeeklyMenuDay).filter(WeeklyMenuDay.menu_id == mid).all()
        assert len(dias) == 7 and all(d.diet_id == a for d in dias), dias
    finally:
        db.close()


def test_un_cliente_ajeno_no_se_toca(client, seed, admin_headers):
    """El coach de otro centro no puede repartirle la semana a este cliente."""
    suf = uuid.uuid4().hex[:8]
    _dc, h_coach, det_cli, _hcli = _monta(client, admin_headers, suf)
    a, _b, _c = _tres_dietas(client, h_coach, det_cli, suf)
    _dc2, h_ajeno, _det2, _h2 = _monta(client, admin_headers, uuid.uuid4().hex[:8])

    r = client.put(f"/api/weekly-menus/client/{det_cli}", headers=h_ajeno,
                   json=_semana([a] * 7))
    assert r.status_code in (403, 404), r.status_code
