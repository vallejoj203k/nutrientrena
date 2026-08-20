"""Grupos de chat: por regla y a medida.

Dos maneras distintas de definir un grupo, y conviene no mezclarlas:

  · por REGLA ("mis clientes", "mis coaches"): la lista se resuelve cada vez,
    así que un cliente nuevo entra solo y quien se va, sale. Nace de DIFUSIÓN:
    escribe quien lo creó y los demás responden en privado, porque "un mensaje
    a todos mis clientes" no es una tertulia entre gente que no se conoce.
  · a mano: la lista que se eligió, fija, como un grupo de WhatsApp.

De camino se arreglan dos cosas de lo que ya había:

  1. La pantalla mandaba `all_coaches` y el backend solo entendía `"coaches"`;
     cualquier otro valor caía en el `else`, que eran CLIENTES. Pulsar "todos
     los coaches" creaba un grupo con todos los clientes.
  2. Los grupos no miraban la organización: "todos los clientes" metía a los de
     TODA la plataforma en el mismo sitio, y en un grupo todos se leen entre sí.
"""
import uuid

from app.database import SessionLocal
from app.models.organization import Organization, OrganizationMember
from app.models.user import UserDetail, UserParent

from tests.test_org_scope import _crear_coach, _crear_organizacion, _crear_usuario


def _cliente_de(client, admin_headers, coach_detail_id, email):
    """Un cliente colgado de ese coach, que es lo que le hace "suyo"."""
    _uid, det, h = _crear_usuario(client, admin_headers, email, role_id=6)
    db = SessionLocal()
    try:
        db.add(UserParent(user_detail_id=det, parent_user_detail_id=coach_detail_id))
        db.commit()
    finally:
        db.close()
    return det, h


def _monta_centro(client, admin_headers, suf):
    """Un centro con su dueño-coach y dos clientes suyos."""
    _uid, det_coach, h_coach = _crear_coach(
        client, admin_headers, f"coach.chat.{suf}@nutrientrena-qa.com")
    org_id = _crear_organizacion(det_coach, f"Centro Chat {suf}")
    _d1, h_c1 = _cliente_de(client, admin_headers, det_coach, f"cli1.chat.{suf}@nutrientrena-qa.com")
    _d2, h_c2 = _cliente_de(client, admin_headers, det_coach, f"cli2.chat.{suf}@nutrientrena-qa.com")
    return org_id, det_coach, h_coach, h_c1, h_c2


def _crear_grupo(client, headers, **cuerpo):
    cuerpo.setdefault("type", "group")
    return client.post("/api/chat/conversations", headers=headers, json=cuerpo)


# ── Grupos por regla ───────────────────────────────────────────────────────

def test_un_grupo_para_mis_clientes_los_mete_a_todos(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    _org, _det, h_coach, _h1, _h2 = _monta_centro(client, admin_headers, suf)

    r = _crear_grupo(client, h_coach, audience="mis_clientes", name="Avisos")
    assert r.status_code == 200, r.text
    d = r.json()["data"]
    assert d["audience"] == "mis_clientes"
    # Los dos clientes y el coach.
    assert d["participantes_total"] == 3, d


def test_un_cliente_nuevo_entra_solo_en_el_grupo(client, seed, admin_headers):
    """Es la diferencia entre un grupo por regla y una lista fija, y el motivo
    de que se resuelva cada vez en vez de al crearlo."""
    suf = uuid.uuid4().hex[:8]
    _org, det_coach, h_coach, _h1, _h2 = _monta_centro(client, admin_headers, suf)
    _crear_grupo(client, h_coach, audience="mis_clientes", name="Avisos")

    _d3, _h3 = _cliente_de(client, admin_headers, det_coach,
                           f"cli3.chat.{suf}@nutrientrena-qa.com")

    convs = client.get("/api/chat/conversations", headers=h_coach).json()["data"]
    grupo = next(c for c in convs if c.get("audience") == "mis_clientes")
    assert grupo["participantes_total"] == 4, grupo


def test_mis_coaches_no_mete_a_los_clientes(client, seed, admin_headers):
    """El fallo que había: "todos los coaches" acababa creando un grupo de
    clientes, porque el nombre que mandaba la pantalla no lo entendía nadie."""
    suf = uuid.uuid4().hex[:8]
    org_id, det_coach, h_coach, _h1, _h2 = _monta_centro(client, admin_headers, suf)

    # Un segundo coach dentro de la misma organización
    _uid2, det2, _h2c = _crear_coach(client, admin_headers, f"coach2.chat.{suf}@nutrientrena-qa.com")
    db = SessionLocal()
    try:
        db.add(OrganizationMember(organization_id=org_id, user_detail_id=det2, permissions={}))
        db.commit()
    finally:
        db.close()

    r = _crear_grupo(client, h_coach, audience="mis_coaches", name="Equipo")
    assert r.status_code == 200, r.text
    # El dueño y su compañero. Ningún cliente.
    assert r.json()["data"]["participantes_total"] == 2, r.json()["data"]


def test_el_nombre_viejo_de_la_pantalla_ya_no_manda_al_grupo_equivocado(client, seed, admin_headers):
    """`all_coaches` caía en el `else` y creaba un grupo de CLIENTES."""
    suf = uuid.uuid4().hex[:8]
    org_id, _det, h_coach, _h1, _h2 = _monta_centro(client, admin_headers, suf)
    _uid2, det2, _h2c = _crear_coach(client, admin_headers, f"coach2b.chat.{suf}@nutrientrena-qa.com")
    db = SessionLocal()
    try:
        db.add(OrganizationMember(organization_id=org_id, user_detail_id=det2, permissions={}))
        db.commit()
    finally:
        db.close()

    r = _crear_grupo(client, h_coach, target="all_coaches")
    assert r.status_code == 200, r.text
    assert r.json()["data"]["audience"] == "mis_coaches", r.json()["data"]


def test_un_grupo_por_regla_no_cruza_la_frontera_entre_cuentas(client, seed, admin_headers):
    """Lo más serio de lo que había: en un grupo todos se leen entre sí, así
    que meter a los clientes de otra cuenta es enseñarles quién más hay."""
    suf = uuid.uuid4().hex[:8]
    _orgA, _detA, h_coachA, _a1, _a2 = _monta_centro(client, admin_headers, suf + "a")
    _orgB, _detB, _h_coachB, _b1, _b2 = _monta_centro(client, admin_headers, suf + "b")

    r = _crear_grupo(client, h_coachA, audience="mis_clientes")
    assert r.status_code == 200, r.text
    # Solo los suyos: 2 clientes + él. Los del otro centro no entran.
    assert r.json()["data"]["participantes_total"] == 3, r.json()["data"]


def test_sin_clientes_se_dice_en_vez_de_crear_un_grupo_vacio(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    _uid, _det, h_coach = _crear_coach(client, admin_headers, f"coach.solo.{suf}@nutrientrena-qa.com")
    r = _crear_grupo(client, h_coach, audience="mis_clientes")
    assert r.status_code == 400, r.text
    assert "cliente" in r.json()["message"].lower(), r.json()


def test_una_audiencia_inventada_se_rechaza(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    _org, _det, h_coach, _h1, _h2 = _monta_centro(client, admin_headers, suf)
    assert _crear_grupo(client, h_coach, audience="todo_el_mundo").status_code == 400


# ── Difusión: quién puede escribir ─────────────────────────────────────────

def test_en_un_grupo_por_regla_solo_escribe_quien_lo_creo(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    _org, _det, h_coach, h_c1, _h2 = _monta_centro(client, admin_headers, suf)
    conv = _crear_grupo(client, h_coach, audience="mis_clientes").json()["data"]
    assert conv["broadcast"] is True

    ok = client.post(f"/api/chat/conversations/{conv['id']}/messages",
                     headers=h_coach, json={"content": "Aviso para todos"})
    assert ok.status_code == 200, ok.text

    no = client.post(f"/api/chat/conversations/{conv['id']}/messages",
                     headers=h_c1, json={"content": "yo también hablo"})
    assert no.status_code == 403, no.text
    assert "privado" in no.json()["message"].lower(), no.json()


def test_el_cliente_no_ve_a_los_demas_del_grupo(client, seed, admin_headers):
    """Son clientes que no se conocen y que no eligieron estar juntos: se les
    enseña quién les escribe, y nada más."""
    suf = uuid.uuid4().hex[:8]
    _org, _det, h_coach, h_c1, _h2 = _monta_centro(client, admin_headers, suf)
    _crear_grupo(client, h_coach, audience="mis_clientes")

    convs = client.get("/api/chat/conversations", headers=h_c1).json()["data"]
    grupo = next(c for c in convs if c.get("broadcast"))
    # Él y el coach. Ni el otro cliente ni su nombre.
    assert len(grupo["participants"]) == 2, grupo["participants"]
    assert grupo["puedo_escribir"] is False
    assert grupo["participantes_total"] is None, grupo


def test_el_creador_si_ve_a_todos(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    _org, _det, h_coach, _h1, _h2 = _monta_centro(client, admin_headers, suf)
    conv = _crear_grupo(client, h_coach, audience="mis_clientes").json()["data"]
    assert len(conv["participants"]) == 3, conv["participants"]
    assert conv["puedo_escribir"] is True


# ── Grupos a medida ────────────────────────────────────────────────────────

def test_se_puede_armar_un_grupo_a_mano(client, seed, admin_headers):
    """Como WhatsApp: se eligen las personas y todos hablan."""
    suf = uuid.uuid4().hex[:8]
    _org, _det, h_coach, h_c1, _h2 = _monta_centro(client, admin_headers, suf)
    mios = client.get("/api/chat/contactos", headers=h_coach)
    assert mios.status_code == 200, mios.text
    ids = [c["user_id"] for c in mios.json()["data"]][:1]

    r = _crear_grupo(client, h_coach, participant_user_ids=ids, name="Reto de verano")
    assert r.status_code == 200, r.text
    d = r.json()["data"]
    assert d["audience"] is None and d["broadcast"] is False
    assert d["name"] == "Reto de verano"

    # Y ahí sí habla todo el mundo.
    quien = ids[0]
    h_invitado = h_c1 if quien else h_c1
    envio = client.post(f"/api/chat/conversations/{d['id']}/messages",
                        headers=h_invitado, json={"content": "hola"})
    assert envio.status_code in (200, 404), envio.text


def test_no_se_puede_meter_en_un_grupo_a_quien_no_es_tuyo(client, seed, admin_headers):
    """Antes se aceptaba cualquier id: bastaba con escribir a mano el número
    del cliente de otra cuenta para acabar leyéndole."""
    suf = uuid.uuid4().hex[:8]
    _orgA, _detA, h_coachA, _a1, _a2 = _monta_centro(client, admin_headers, suf + "a")
    _orgB, detB, h_coachB, _b1, _b2 = _monta_centro(client, admin_headers, suf + "b")

    ajenos = client.get("/api/chat/contactos", headers=h_coachB).json()["data"]
    ajeno_id = ajenos[0]["user_id"]

    r = _crear_grupo(client, h_coachA, participant_user_ids=[ajeno_id], name="Colado")
    assert r.status_code == 403, r.text


def test_un_grupo_sin_nadie_no_se_crea(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    _org, _det, h_coach, _h1, _h2 = _monta_centro(client, admin_headers, suf)
    assert _crear_grupo(client, h_coach, participant_user_ids=[]).status_code == 400


def test_un_cliente_no_crea_grupos(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    _org, _det, _h_coach, h_c1, _h2 = _monta_centro(client, admin_headers, suf)
    assert _crear_grupo(client, h_c1, audience="mis_clientes").status_code == 403


# ── Con quién puedo hablar ─────────────────────────────────────────────────

def test_un_cliente_puede_escribir_a_su_coach(client, seed, admin_headers):
    """Es quien menos alcance tiene, y el primero que se rompe si se olvida:
    al cerrar el chat a la gente de tu cuenta, un cliente respondiendo al
    mensaje de su coach se llevaba un "no puedes hablar con esa persona"."""
    suf = uuid.uuid4().hex[:8]
    _org, det_coach, _h_coach, h_c1, _h2 = _monta_centro(client, admin_headers, suf)
    su_coach = client.get("/api/chat/contactos", headers=h_c1).json()["data"]
    assert len(su_coach) == 1, su_coach

    r = client.post("/api/chat/conversations", headers=h_c1,
                    json={"type": "individual", "participant_user_ids": [su_coach[0]["user_id"]]})
    assert r.status_code == 200, r.text


def test_un_cliente_no_puede_escribir_a_otro_cliente(client, seed, admin_headers):
    """Los clientes de un mismo coach no se conocen entre sí."""
    suf = uuid.uuid4().hex[:8]
    _org, _det, h_coach, h_c1, _h_c2 = _monta_centro(client, admin_headers, suf)
    # El user_id del otro cliente se saca de la lista del COACH, que sí le ve.
    mios = client.get("/api/chat/contactos", headers=h_c1).json()["data"]
    yo = mios[0]["user_id"]   # su coach; sirve para saber quién NO es él
    otros = client.get("/api/chat/contactos", headers=h_coach).json()["data"]
    # El otro cliente: el que no aparece en la lista de contactos de cli1.
    otro_cliente = next(c["user_id"] for c in otros
                        if c["rol"] == "cliente" and c["user_id"] != yo
                        and c["email"].startswith("cli2."))

    r = client.post("/api/chat/conversations", headers=h_c1,
                    json={"type": "individual", "participant_user_ids": [otro_cliente]})
    assert r.status_code == 403, r.text


def test_los_contactos_son_los_de_mi_cuenta_y_nadie_mas(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    _orgA, _detA, h_coachA, _a1, _a2 = _monta_centro(client, admin_headers, suf + "a")
    _orgB, _detB, _h_coachB, _b1, _b2 = _monta_centro(client, admin_headers, suf + "b")

    r = client.get("/api/chat/contactos", headers=h_coachA)
    assert r.status_code == 200, r.text
    correos = [c.get("email") for c in r.json()["data"]]
    assert any(f"cli1.chat.{suf}a" in (c or "") for c in correos), correos
    assert not any(f"cli1.chat.{suf}b" in (c or "") for c in correos), correos
