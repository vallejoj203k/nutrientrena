"""Sección "Analíticas" del panel de plataforma.

Todo lo que sale de aquí alimenta decisiones, así que la regla es dura: o el
número sale de datos reales, o va en null. Un panel que enseña un MRR creíble
y falso es peor que uno que enseña un hueco.

Lo que más se prueba: que las altas por mes cuenten lo que dicen, que el
acumulado no se olvide de lo anterior a la ventana, y que la retención por
cohorte distinga un mes que no ha pasado todavía (hueco) de un mes en el que
nadie hizo nada (0%). Confundir esos dos es lo que hace que una tabla de
cohortes mienta.
"""
from datetime import date, datetime

from app.core.dependencies import SOPORTE
from app.database import SessionLocal
from app.models.organization import Organization
from app.models.session_log import WorkoutSession
from app.models.user import User, UserDetail, UserParent

from tests.test_admin_panel import _con_rol
from tests.test_org_scope import _crear_organizacion, _crear_usuario


def _analiticas(client, headers):
    r = client.get("/api/admin/analytics", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()["data"]


def _mes(f) -> str:
    return f"{f.year:04d}-{f.month:02d}"


def _hace_meses(n: int) -> datetime:
    """Un día 15 para no tropezar con los meses de 30 y 31 días."""
    hoy = date.today()
    total = hoy.year * 12 + (hoy.month - 1) - n
    return datetime(total // 12, total % 12 + 1, 15)


def _envejecer(org_id: str, cuando: datetime):
    db = SessionLocal()
    try:
        db.query(Organization).filter(Organization.id == org_id).first().created_at = cuando
        db.commit()
    finally:
        db.close()


def _cliente_con_entrenamiento(client, headers, coach_detail_id, nombre, fechas):
    email = f"{nombre.lower().replace(' ', '.')}@nutrientrena-qa.com"
    r = client.post("/api/users", headers=headers,
                    json={"name": nombre, "email": email, "password": "Cliente123!", "role_id": 6})
    assert r.status_code == 200, r.text
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.email == email).first()
        d = db.query(UserDetail).filter(UserDetail.user_id == u.id).first()
        db.add(UserParent(user_detail_id=d.id, parent_user_detail_id=coach_detail_id))
        for f in fechas:
            db.add(WorkoutSession(client_user_detail_id=d.id, session_date=f))
        db.commit()
        return d.id
    finally:
        db.close()


# ── Quién entra ─────────────────────────────────────────────────────────────

def test_solo_el_equipo_de_plataforma_ve_las_analiticas(client, seed, admin_headers):
    assert client.get("/api/admin/analytics", headers=admin_headers).status_code == 200

    _uid, _det, h = _crear_usuario(client, admin_headers, "coach.ana.fuera@nutrientrena-qa.com", role_id=5)
    assert client.get("/api/admin/analytics", headers=h).status_code == 403

    # Soporte tampoco: su sección es soporte, no las métricas del negocio
    _uid2, _det2, h2 = _con_rol(client, admin_headers, "soporte.ana@nutrientrena-qa.com", SOPORTE)
    assert client.get("/api/admin/analytics", headers=h2).status_code == 403


# ── Lo que no se inventa ────────────────────────────────────────────────────

def test_mrr_y_arpa_llegan_vacios_a_proposito(client, seed, admin_headers):
    """Son lo que las cuentas le pagan a Alzum, y eso no existe en ninguna
    tabla hasta que haya pasarela. Rellenarlos con lo que los coaches cobran a
    SUS clientes daría un número creíble y falso."""
    k = _analiticas(client, admin_headers)["kpis"]
    assert k["mrr"] is None and k["arpa"] is None


# ── Altas y acumulado ───────────────────────────────────────────────────────

def test_las_altas_se_cuentan_en_el_mes_que_toca(client, seed, admin_headers):
    _uid, det, _h = _crear_usuario(client, admin_headers, "duenio.ana.altas@nutrientrena-qa.com", role_id=2)
    org_id = _crear_organizacion(det, "Centro de hace dos meses")
    cuando = _hace_meses(2)
    _envejecer(org_id, cuando)

    datos = _analiticas(client, admin_headers)
    por_mes = {x["mes"]: x["valor"] for x in datos["altas_por_mes"]}
    assert _mes(cuando) in por_mes, por_mes
    assert por_mes[_mes(cuando)] >= 1


def test_el_acumulado_no_se_olvida_de_lo_anterior_a_la_ventana(client, seed, admin_headers):
    """Se enseñan siete meses, pero la plataforma no nació hace siete meses. Si
    el acumulado empezara en cero, la primera columna diría que hay menos
    cuentas de las que hay."""
    _uid, det, _h = _crear_usuario(client, admin_headers, "duenio.ana.vieja@nutrientrena-qa.com", role_id=2)
    _envejecer(_crear_organizacion(det, "Centro muy antiguo"), _hace_meses(24))

    datos = _analiticas(client, admin_headers)
    acumulado = datos["acumulado"]
    assert acumulado[0]["valor"] >= 1, acumulado

    # Y nunca baja: es acumulado
    valores = [x["valor"] for x in acumulado]
    assert valores == sorted(valores), valores

    # El último acumulado es el total de cuentas
    assert acumulado[-1]["valor"] == datos["kpis"]["cuentas"]


def test_la_ventana_es_de_siete_meses_como_el_prototipo(client, seed, admin_headers):
    datos = _analiticas(client, admin_headers)
    assert len(datos["altas_por_mes"]) == 7
    assert len(datos["acumulado"]) == 7
    # En orden, del más antiguo al más reciente
    meses = [x["mes"] for x in datos["altas_por_mes"]]
    assert meses == sorted(meses)
    assert meses[-1] == _mes(date.today())


# ── Indicadores reales ──────────────────────────────────────────────────────

def test_clientes_por_coach_sale_de_los_datos(client, seed, admin_headers):
    _uid, det, _h = _crear_usuario(client, admin_headers, "duenio.ana.ratio@nutrientrena-qa.com", role_id=2)
    _crear_organizacion(det, "Centro con dos clientes")
    _cliente_con_entrenamiento(client, admin_headers, det, "Ratio Uno", [])
    _cliente_con_entrenamiento(client, admin_headers, det, "Ratio Dos", [])

    k = _analiticas(client, admin_headers)["kpis"]
    assert k["clientes"] >= 2 and k["coaches"] >= 1
    assert k["clientes_por_coach"] == round(k["clientes"] / k["coaches"], 1)


def test_las_cuentas_caidas_son_las_suspendidas_e_impagadas(client, seed, admin_headers):
    _uid, det, _h = _crear_usuario(client, admin_headers, "duenio.ana.caida@nutrientrena-qa.com", role_id=2)
    org_id = _crear_organizacion(det, "Centro que se cae")

    antes = _analiticas(client, admin_headers)["kpis"]["cuentas_caidas"]
    r = client.put(f"/api/admin/organizations/{org_id}/state", headers=admin_headers,
                   json={"state": "suspendida"})
    assert r.status_code == 200, r.text
    assert _analiticas(client, admin_headers)["kpis"]["cuentas_caidas"] == antes + 1


# ── Retención por cohorte ───────────────────────────────────────────────────

def test_una_cuenta_con_actividad_se_retiene_y_sin_ella_no(client, seed, admin_headers):
    """Se mide por lo que hacen sus CLIENTES. Una cuenta con cincuenta rutinas
    creadas hace un año y nadie entrenando está muerta."""
    alta = _hace_meses(2)

    _uid_v, det_v, _hv = _crear_usuario(client, admin_headers, "duenio.ana.viva@nutrientrena-qa.com", role_id=2)
    org_viva = _crear_organizacion(det_v, "Centro vivo")
    _envejecer(org_viva, alta)
    # Un entrenamiento el mes siguiente al alta
    _cliente_con_entrenamiento(client, admin_headers, det_v, "Cliente Vivo",
                               [_hace_meses(1).date()])

    _uid_m, det_m, _hm = _crear_usuario(client, admin_headers, "duenio.ana.muerta@nutrientrena-qa.com", role_id=2)
    org_muerta = _crear_organizacion(det_m, "Centro muerto")
    _envejecer(org_muerta, alta)
    _cliente_con_entrenamiento(client, admin_headers, det_m, "Cliente Callado", [])

    datos = _analiticas(client, admin_headers)
    fila = next((c for c in datos["cohortes"] if c["cohorte"] == _mes(alta)), None)
    assert fila is not None, datos["cohortes"]

    # Mes 0 es 100% por definición: acaban de entrar
    assert fila["valores"][0] == 100
    # Mes 1: una de las dos siguió viva -> ni 0 ni 100
    assert fila["valores"][1] is not None
    assert 0 < fila["valores"][1] < 100, fila


def test_un_mes_que_no_ha_pasado_es_un_hueco_no_un_cero(client, seed, admin_headers):
    """Confundir "todavía no ha llegado" con "nadie hizo nada" es lo que hace
    que una tabla de cohortes mienta: la cohorte de este mes parecería tener un
    0% de retención a tres meses."""
    _uid, det, _h = _crear_usuario(client, admin_headers, "duenio.ana.hoy@nutrientrena-qa.com", role_id=2)
    org_id = _crear_organizacion(det, "Centro de este mes")
    _envejecer(org_id, datetime.now())

    datos = _analiticas(client, admin_headers)
    fila = next(c for c in datos["cohortes"] if c["cohorte"] == _mes(date.today()))
    assert fila["valores"][0] == 100
    assert fila["valores"][1] is None and fila["valores"][2] is None and fila["valores"][3] is None, fila


def test_las_cohortes_salen_de_la_mas_antigua_a_la_mas_reciente(client, seed, admin_headers):
    for n in (1, 3):
        _uid, det, _h = _crear_usuario(client, admin_headers,
                                       f"duenio.ana.orden{n}@nutrientrena-qa.com", role_id=2)
        _envejecer(_crear_organizacion(det, f"Centro orden {n}"), _hace_meses(n))

    cohortes = [c["cohorte"] for c in _analiticas(client, admin_headers)["cohortes"]]
    assert cohortes == sorted(cohortes), cohortes


def test_la_actividad_de_otra_cuenta_no_retiene_a_la_tuya(client, seed, admin_headers):
    """Si el cruce cliente → cuenta estuviera mal, la retención saldría bien
    por accidente en cuanto alguien de la plataforma entrenara.

    Usa un mes que no usa ningún otro test de este fichero: la base es
    compartida, y si otra cuenta cayera en la misma cohorte el porcentaje ya no
    hablaría solo de la de aquí.
    """
    alta = _hace_meses(4)
    _uid_a, det_a, _ha = _crear_usuario(client, admin_headers, "duenio.ana.cruceA@nutrientrena-qa.com", role_id=2)
    org_a = _crear_organizacion(det_a, "Centro cruce A")
    _envejecer(org_a, alta)
    _cliente_con_entrenamiento(client, admin_headers, det_a, "Cruce Callado", [])

    _uid_b, det_b, _hb = _crear_usuario(client, admin_headers, "duenio.ana.cruceB@nutrientrena-qa.com", role_id=2)
    org_b = _crear_organizacion(det_b, "Centro cruce B")
    _envejecer(org_b, _hace_meses(6))   # otra cohorte, para no mezclarse
    _cliente_con_entrenamiento(client, admin_headers, det_b, "Cruce Activo",
                               [(_hace_meses(2)).date(), (_hace_meses(1)).date()])

    fila = next(c for c in _analiticas(client, admin_headers)["cohortes"]
                if c["cohorte"] == _mes(alta))
    # Solo está A en esa cohorte, y A no tiene actividad: 0%, no 100%
    assert fila["cuentas"] == 1, fila
    assert fila["valores"][1] == 0, fila


def test_una_cuenta_sin_clientes_no_rompe_nada(client, seed, admin_headers):
    _uid, det, _h = _crear_usuario(client, admin_headers, "duenio.ana.vacio@nutrientrena-qa.com", role_id=2)
    _envejecer(_crear_organizacion(det, "Centro sin clientes"), _hace_meses(2))
    datos = _analiticas(client, admin_headers)
    assert isinstance(datos["cohortes"], list)
    assert datos["kpis"]["clientes_por_coach"] >= 0


def test_el_alta_de_hoy_aparece_en_el_ultimo_mes(client, seed, admin_headers):
    antes = _analiticas(client, admin_headers)["altas_por_mes"][-1]["valor"]
    _uid, det, _h = _crear_usuario(client, admin_headers, "duenio.ana.hoy2@nutrientrena-qa.com", role_id=2)
    _crear_organizacion(det, "Centro creado ahora")
    despues = _analiticas(client, admin_headers)["altas_por_mes"][-1]
    assert despues["mes"] == _mes(date.today())
    assert despues["valor"] == antes + 1


def test_la_actividad_se_apunta_en_el_mes_en_que_ocurrio(client, seed, admin_headers):
    """Un entrenamiento de hace ocho meses no puede retener la cohorte del mes
    pasado.

    Se comprueba sobre el mapa cuenta → meses con actividad en vez de sobre el
    porcentaje de la cohorte: el porcentaje mezcla a todas las cuentas de ese
    mes, y la base de pruebas es compartida. Aquí se mira solo esta.
    """
    from app.routers.admin_panel import _meses_activos_por_organizacion

    _uid, det, _h = _crear_usuario(client, admin_headers, "duenio.ana.fechas@nutrientrena-qa.com", role_id=2)
    org_id = _crear_organizacion(det, "Centro con actividad vieja")
    _envejecer(org_id, _hace_meses(3))
    _cliente_con_entrenamiento(client, admin_headers, det, "Fechas Antiguas",
                               [_hace_meses(8).date()])

    db = SessionLocal()
    try:
        activos = _meses_activos_por_organizacion(db)
    finally:
        db.close()

    assert activos.get(org_id) == {_mes(_hace_meses(8))}, activos.get(org_id)


def test_las_fechas_futuras_no_aparecen_en_la_ventana(client, seed, admin_headers):
    """Comprobación de cordura sobre el cálculo de meses: nada posterior a hoy
    debe colarse en el eje."""
    datos = _analiticas(client, admin_headers)
    hoy = _mes(date.today())
    assert all(x["mes"] <= hoy for x in datos["altas_por_mes"])
    assert all(c["cohorte"] <= hoy for c in datos["cohortes"])


def test_diciembre_no_rompe_el_salto_de_ano(client, seed, admin_headers):
    """El cálculo de meses se hace a mano; un fallo aquí solo se vería en
    enero."""
    from app.routers.admin_panel import _sumar_meses
    assert _sumar_meses("2025-12", 1) == "2026-01"
    assert _sumar_meses("2026-01", -1) == "2025-12"
    assert _sumar_meses("2026-01", -13) == "2024-12"
    assert _sumar_meses("2025-11", 3) == "2026-02"


def test_los_totales_cuadran_con_la_seccion_de_coaches(client, seed, admin_headers):
    """Dos pantallas que cuentan lo mismo de forma distinta acaban diciendo
    cosas distintas, y entonces no se cree ninguna."""
    a = _analiticas(client, admin_headers)["kpis"]
    b = client.get("/api/admin/organizations", headers=admin_headers).json()["data"]["totales"]
    assert a["cuentas"] == b["cuentas"]
    assert a["clientes"] == b["clientes"]
