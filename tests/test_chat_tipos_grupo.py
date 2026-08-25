"""Las tres clases de grupo, y por qué no son intercambiables.

La pantalla de "Nuevo grupo" pide elegir qué clase de grupo es antes de elegir
a quién se mete. No es adorno: la clase decide quién puede estar dentro.

  · `equipo`      — solo el equipo. Meter a un cliente en el grupo interno le
                    deja leer cómo se habla de los clientes.
  · `comunidad`   — el coach con sus clientes: un reto, un grupo de ánimo. Aquí
                    los clientes SÍ se ven entre ellos, al revés que en el
                    aviso a todos, que va uno a uno.
  · `seguimiento` — un cliente con quien lo lleva: hace falta al menos un
                    cliente y al menos alguien del equipo.

Se comprueba en el SERVIDOR y no solo en la pantalla porque quien manda la
petición a mano se salta el filtro: sin esto, un id escrito a mano metía a un
cliente en el grupo interno del equipo.
"""
import uuid

from app.database import SessionLocal
from app.models.team_member import TeamMember
from app.models.user import UserDetail, UserParent

from tests.test_org_scope import _crear_coach, _crear_organizacion, _crear_usuario


def _monta(client, admin_headers, suf):
    """Un centro con su coach, un miembro del equipo y dos clientes."""
    _u, det_coach, h_coach = _crear_coach(
        client, admin_headers, f"coach.tg.{suf}@nutrientrena-qa.com")
    org_id = _crear_organizacion(det_coach, f"Centro TG {suf}")

    # Alguien del equipo, con su oficio puesto.
    uid_pro, det_pro, _h = _crear_coach(
        client, admin_headers, f"nutri.tg.{suf}@nutrientrena-qa.com")
    clientes = []
    db = SessionLocal()
    try:
        from app.models.organization import OrganizationMember
        db.add(OrganizationMember(organization_id=org_id, user_detail_id=det_pro))
        db.add(TeamMember(user_detail_id=det_pro, organization_id=org_id,
                          member_name="Nutri TG", role_label="Nutricionista"))
        db.commit()
    finally:
        db.close()

    for n in ("uno", "dos"):
        _uid, det, _hc = _crear_usuario(
            client, admin_headers, f"cli{n}.tg.{suf}@nutrientrena-qa.com", role_id=6)
        db = SessionLocal()
        try:
            db.add(UserParent(user_detail_id=det, parent_user_detail_id=det_coach))
            db.commit()
            clientes.append(db.query(UserDetail).filter(UserDetail.id == det).first().user_id)
        finally:
            db.close()
    return h_coach, uid_pro, clientes


def _crear(client, h, **cuerpo):
    cuerpo.setdefault("type", "group")
    return client.post("/api/chat/conversations", headers=h, json=cuerpo)


# ── Cada clase admite a unos y no a otros ──────────────────────────────────

def test_UN_GRUPO_DE_EQUIPO_NO_ADMITE_CLIENTES(client, seed, admin_headers):
    """Lo que de verdad protege esto: el grupo interno es donde se habla DE los
    clientes. Uno dentro lo lee todo."""
    suf = uuid.uuid4().hex[:8]
    h_coach, uid_pro, clientes = _monta(client, admin_headers, suf)

    ok = _crear(client, h_coach, tipo="equipo", name=f"Equipo {suf}",
                participant_user_ids=[uid_pro])
    assert ok.status_code == 200, ok.text

    mal = _crear(client, h_coach, tipo="equipo", name=f"Equipo malo {suf}",
                 participant_user_ids=[uid_pro, clientes[0]])
    assert mal.status_code == 422, mal.text
    assert "cliente" in mal.json()["message"].lower(), mal.json()


def test_una_comunidad_necesita_al_menos_un_cliente(client, seed, admin_headers):
    """Una "comunidad de clientes" solo con el equipo dentro no es una
    comunidad: es un grupo de equipo con otro nombre."""
    suf = uuid.uuid4().hex[:8]
    h_coach, uid_pro, clientes = _monta(client, admin_headers, suf)

    ok = _crear(client, h_coach, tipo="comunidad", name=f"Reto {suf}",
                participant_user_ids=clientes)
    assert ok.status_code == 200, ok.text

    mal = _crear(client, h_coach, tipo="comunidad", name=f"Reto malo {suf}",
                 participant_user_ids=[uid_pro])
    assert mal.status_code == 422, mal.text


def test_UN_SEGUIMIENTO_NECESITA_CLIENTE_Y_EQUIPO(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    h_coach, uid_pro, clientes = _monta(client, admin_headers, suf)

    ok = _crear(client, h_coach, tipo="seguimiento", name=f"Seguimiento {suf}",
                participant_user_ids=[uid_pro, clientes[0]])
    assert ok.status_code == 200, ok.text

    # Solo el cliente: falta quien lo lleva.
    sin_pro = _crear(client, h_coach, tipo="seguimiento", name="x",
                     participant_user_ids=[clientes[0]])
    assert sin_pro.status_code == 422, sin_pro.text
    # Solo el equipo: falta el cliente al que se hace seguimiento.
    sin_cli = _crear(client, h_coach, tipo="seguimiento", name="x",
                     participant_user_ids=[uid_pro])
    assert sin_cli.status_code == 422, sin_cli.text


def test_un_tipo_inventado_se_rechaza(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    h_coach, uid_pro, _c = _monta(client, admin_headers, suf)
    r = _crear(client, h_coach, tipo="loquesea", name="x", participant_user_ids=[uid_pro])
    assert r.status_code == 422, r.text


def test_un_grupo_vacio_no_se_crea(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    h_coach, _p, _c = _monta(client, admin_headers, suf)
    assert _crear(client, h_coach, tipo="equipo", name="x",
                  participant_user_ids=[]).status_code in (400, 422)


# ── Cómo queda el grupo una vez creado ─────────────────────────────────────

def test_LOS_TRES_TIPOS_SE_HABLAN_ENTRE_ELLOS_no_son_difusion(client, seed, admin_headers):
    """La diferencia con el "aviso a todos": en un reto los clientes se
    responden entre ellos. Si naciera de difusión, solo escribiría el coach y
    el grupo de motivación no motivaría a nadie."""
    suf = uuid.uuid4().hex[:8]
    h_coach, uid_pro, clientes = _monta(client, admin_headers, suf)

    r = _crear(client, h_coach, tipo="comunidad", name=f"Reto {suf}",
               participant_user_ids=clientes)
    assert r.json()["data"]["broadcast"] is False, r.json()["data"]
    assert r.json()["data"]["puedo_escribir"] is True, r.json()["data"]


def test_el_aviso_a_todos_los_clientes_sigue_siendo_difusion(client, seed, admin_headers):
    """Lo que ya había no se rompe: es la única clase donde los clientes NO se
    ven entre ellos y donde los nuevos entran solos."""
    suf = uuid.uuid4().hex[:8]
    h_coach, _p, _c = _monta(client, admin_headers, suf)
    r = _crear(client, h_coach, audience="mis_clientes", name=f"Aviso {suf}")
    assert r.status_code == 200, r.text
    assert r.json()["data"]["broadcast"] is True, r.json()["data"]


def test_el_que_lo_crea_entra_en_el_grupo(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    h_coach, uid_pro, _c = _monta(client, admin_headers, suf)
    r = _crear(client, h_coach, tipo="equipo", name=f"Equipo {suf}",
               participant_user_ids=[uid_pro])
    assert r.json()["data"]["participantes_total"] == 2, r.json()["data"]


def test_no_se_puede_meter_a_gente_de_otra_cuenta(client, seed, admin_headers):
    """La comprobación de siempre sigue en pie: elegir el tipo no abre la
    puerta a meter al cliente de otro centro."""
    suf = uuid.uuid4().hex[:8]
    h_coach, _p, _c = _monta(client, admin_headers, suf)
    _h2, _p2, ajenos = _monta(client, admin_headers, uuid.uuid4().hex[:8])

    r = _crear(client, h_coach, tipo="comunidad", name="x",
               participant_user_ids=[ajenos[0]])
    assert r.status_code == 403, r.text


# ── Gestionar el grupo ya creado ───────────────────────────────────────────
#
# El nombre solo se ponía al crearlo. Un grupo que nació "Reto enero" y sigue
# en marcha en marzo se queda con un nombre que ya no es verdad, y la única
# salida era rehacerlo y perder la conversación entera.

def test_SE_LE_PUEDE_CAMBIAR_EL_NOMBRE_A_UN_GRUPO(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    h_coach, uid_pro, _c = _monta(client, admin_headers, suf)
    conv = _crear(client, h_coach, tipo="equipo", name=f"Reto enero {suf}",
                  participant_user_ids=[uid_pro]).json()["data"]["id"]

    r = client.patch(f"/api/chat/conversations/{conv}", headers=h_coach,
                     json={"name": f"Reto marzo {suf}"})
    assert r.status_code == 200, r.text
    assert r.json()["data"]["name"] == f"Reto marzo {suf}", r.json()["data"]

    # Y se queda cambiado, no solo en la respuesta.
    convs = client.get("/api/chat/conversations", headers=h_coach).json()["data"]
    assert [c for c in convs if c["id"] == conv][0]["name"] == f"Reto marzo {suf}"


def test_un_nombre_en_blanco_no_vale(client, seed, admin_headers):
    """Un grupo sin nombre sale como "Grupo" en la lista, y con tres grupos
    todos se llaman igual."""
    suf = uuid.uuid4().hex[:8]
    h_coach, uid_pro, _c = _monta(client, admin_headers, suf)
    conv = _crear(client, h_coach, tipo="equipo", name=f"Equipo {suf}",
                  participant_user_ids=[uid_pro]).json()["data"]["id"]

    assert client.patch(f"/api/chat/conversations/{conv}", headers=h_coach,
                        json={"name": "   "}).status_code == 422


def test_SOLO_QUIEN_LO_CREO_LE_CAMBIA_EL_NOMBRE(client, seed, admin_headers):
    """Es quien reunió a esa gente. Si lo renombrara cualquiera, el grupo
    cambiaría de nombre en la lista de todos sin que nadie sepa quién."""
    suf = uuid.uuid4().hex[:8]
    h_coach, uid_pro, _c = _monta(client, admin_headers, suf)
    conv = _crear(client, h_coach, tipo="equipo", name=f"Equipo {suf}",
                  participant_user_ids=[uid_pro]).json()["data"]["id"]

    _h2, _p2, _c2 = _monta(client, admin_headers, uuid.uuid4().hex[:8])
    r = client.patch(f"/api/chat/conversations/{conv}", headers=_h2,
                     json={"name": "Mio ahora"})
    assert r.status_code in (403, 404), r.status_code


def test_a_un_grupo_por_regla_no_se_le_cambia_el_nombre_a_mano(client, seed, admin_headers):
    """Igual que no se le añade gente a mano: lo define la regla."""
    suf = uuid.uuid4().hex[:8]
    h_coach, _p, _c = _monta(client, admin_headers, suf)
    conv = _crear(client, h_coach, audience="mis_clientes",
                  name=f"Aviso {suf}").json()["data"]["id"]

    r = client.patch(f"/api/chat/conversations/{conv}", headers=h_coach,
                     json={"name": "Otro nombre"})
    assert r.status_code == 400, r.text


def test_los_participantes_dicen_quien_es_quien(client, seed, admin_headers):
    """La ventana de gestionar separa equipo de clientes: en un seguimiento hay
    de los dos y no es lo mismo sacar a la nutricionista que sacar al cliente."""
    suf = uuid.uuid4().hex[:8]
    h_coach, uid_pro, clientes = _monta(client, admin_headers, suf)
    conv = _crear(client, h_coach, tipo="seguimiento", name=f"Seguimiento {suf}",
                  participant_user_ids=[uid_pro, clientes[0]]).json()["data"]

    por_id = {p["user_id"]: p for p in conv["participants"]}
    assert por_id[uid_pro]["rol"] == "coach", por_id[uid_pro]
    assert por_id[uid_pro]["etiqueta"] == "Nutricionista", por_id[uid_pro]
    assert por_id[clientes[0]]["rol"] == "cliente", por_id[clientes[0]]


# ── Lo que la pantalla necesita para pintar la lista ───────────────────────

def test_los_contactos_traen_el_oficio_de_cada_uno(client, seed, admin_headers):
    """Al montar un seguimiento se elige por el oficio —"la nutricionista"—, no
    por el nombre. Sin la etiqueta hay que acordarse de quién es quién."""
    suf = uuid.uuid4().hex[:8]
    h_coach, uid_pro, clientes = _monta(client, admin_headers, suf)

    r = client.get("/api/chat/contactos", headers=h_coach)
    assert r.status_code == 200, r.text
    por_id = {c["user_id"]: c for c in r.json()["data"]}

    assert por_id[uid_pro]["etiqueta"] == "Nutricionista", por_id[uid_pro]
    assert por_id[uid_pro]["rol"] == "coach", por_id[uid_pro]
    # Y los clientes salen como clientes, que es lo que filtra cada tipo.
    assert por_id[clientes[0]]["rol"] == "cliente", por_id[clientes[0]]
