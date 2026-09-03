"""Abrir el chat con una persona concreta, sin buscarla en la lista.

Hacía falta para poder chatear desde la ficha del cliente, pero arregla algo
más: hasta ahora cada pantalla buscaba la conversación entre las que tuviera
CARGADAS y, si no la encontraba, creaba otra. Con la lista paginada basta con
no haber cargado la página donde estaba para acabar con dos conversaciones
con la misma persona, y los mensajes repartidos entre las dos — cada uno
creyendo que el otro no contesta.

Lo que hay que dejar sujeto:

  · Que devuelva SIEMPRE la misma, y que si ya hay mensajes vengan con ella.
  · Que no se pueda abrir el chat del cliente de otra cuenta cambiando el
    número de la URL.
  · Y que no se pueda abrir una conversación con uno mismo, que es una fila en
    la lista que no lleva a nadie.
"""
import uuid

from app.database import SessionLocal
from app.models.chat import ChatConversation, ChatParticipant
from app.models.user import UserParent

from tests.test_org_scope import _crear_coach, _crear_usuario


def _monta(client, admin_headers, suf, quien="a"):
    uid_coach, det_coach, h_coach = _crear_coach(
        client, admin_headers, f"coach.cc.{quien}.{suf}@nutrientrena-qa.com")
    uid_cli, det_cli, h_cli = _crear_usuario(
        client, admin_headers, f"cli.cc.{quien}.{suf}@nutrientrena-qa.com", role_id=6)
    db = SessionLocal()
    try:
        db.add(UserParent(user_detail_id=det_cli, parent_user_detail_id=det_coach))
        db.commit()
    finally:
        db.close()
    return uid_coach, h_coach, uid_cli, h_cli


def _con(client, headers, user_id):
    return client.get(f"/api/chat/con/{user_id}", headers=headers)


def _cuantas(user_id):
    """Conversaciones individuales de esa persona."""
    db = SessionLocal()
    try:
        ids = [p.conversation_id for p in db.query(ChatParticipant).filter(
            ChatParticipant.user_id == user_id).all()]
        if not ids:
            return 0
        return db.query(ChatConversation).filter(
            ChatConversation.id.in_(ids),
            ChatConversation.type == "individual").count()
    finally:
        db.close()


# ── Abrir la conversación ──────────────────────────────────────────────────

def test_se_crea_la_primera_vez(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    _uc, h_coach, uid_cli, _h = _monta(client, admin_headers, suf)

    r = _con(client, h_coach, uid_cli)
    assert r.status_code == 200, r.text
    d = r.json()["data"]
    assert d["type"] == "individual"
    assert d.get("creada") is True
    assert _cuantas(uid_cli) == 1


def test_LA_SEGUNDA_VEZ_ES_LA_MISMA_NO_OTRA(client, seed, admin_headers):
    """Es el fallo que esto viene a cerrar: dos conversaciones con la misma
    persona y los mensajes repartidos entre las dos."""
    suf = uuid.uuid4().hex[:8]
    _uc, h_coach, uid_cli, _h = _monta(client, admin_headers, suf)

    primera = _con(client, h_coach, uid_cli).json()["data"]
    segunda = _con(client, h_coach, uid_cli).json()["data"]

    assert segunda["id"] == primera["id"], "ha creado una conversación nueva"
    assert segunda.get("creada") is False
    assert _cuantas(uid_cli) == 1, "hay más de una conversación con el mismo cliente"


def test_el_cliente_llega_a_LA_MISMA_conversacion(client, seed, admin_headers):
    """El cliente entra por su propia puerta (`/client/chat`). Si cada uno
    abriera la suya, se escribirían sin verse."""
    suf = uuid.uuid4().hex[:8]
    _uc, h_coach, uid_cli, h_cli = _monta(client, admin_headers, suf)

    del_coach = _con(client, h_coach, uid_cli).json()["data"]["id"]
    r = client.get("/api/client/chat", headers=h_cli)
    assert r.status_code == 200, r.text
    assert r.json()["data"]["conversation_id"] == del_coach, \
        "el coach y el cliente están en conversaciones distintas"


def test_los_mensajes_de_esa_conversacion_se_leen(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    _uc, h_coach, uid_cli, h_cli = _monta(client, admin_headers, suf)
    conv = _con(client, h_coach, uid_cli).json()["data"]["id"]

    client.post(f"/api/chat/conversations/{conv}/messages",
                headers=h_coach, json={"content": "Hola, ¿qué tal la semana?"})
    client.post(f"/api/chat/conversations/{conv}/messages",
                headers=h_cli, json={"content": "Bien, subo el check-in"})

    r = client.get(f"/api/chat/conversations/{conv}/messages", headers=h_coach)
    assert r.status_code == 200, r.text
    d = r.json()["data"]
    textos = [m["content"] for m in (d if isinstance(d, list) else d.get("messages", []))]
    assert "Hola, ¿qué tal la semana?" in textos, textos
    assert "Bien, subo el check-in" in textos, textos


def test_abrirla_de_nuevo_trae_los_mensajes_que_ya_habia(client, seed, admin_headers):
    """Abrir el chat desde la ficha no puede empezar de cero: la conversación
    ya existía y tiene su historia."""
    suf = uuid.uuid4().hex[:8]
    _uc, h_coach, uid_cli, _h = _monta(client, admin_headers, suf)
    conv = _con(client, h_coach, uid_cli).json()["data"]["id"]
    client.post(f"/api/chat/conversations/{conv}/messages",
                headers=h_coach, json={"content": "Primer mensaje"})

    otra_vez = _con(client, h_coach, uid_cli).json()["data"]
    assert otra_vez["id"] == conv
    r = client.get(f"/api/chat/conversations/{conv}/messages", headers=h_coach)
    d = r.json()["data"]
    msgs = d if isinstance(d, list) else d.get("messages", [])
    assert any(m["content"] == "Primer mensaje" for m in msgs), msgs


# ── De quién es cada cliente ───────────────────────────────────────────────

def test_NO_SE_ABRE_EL_CHAT_DEL_CLIENTE_DE_OTRO(client, seed, admin_headers):
    """El id va en la URL: sin comprobarlo, bastaba con cambiar el número para
    escribirle al cliente de otra cuenta."""
    suf = uuid.uuid4().hex[:8]
    _u1, _h_mio, uid_mio, _h2 = _monta(client, admin_headers, suf, "mio")
    _u3, h_otro, _uid_otro, _h4 = _monta(client, admin_headers, suf, "otro")

    r = _con(client, h_otro, uid_mio)
    assert r.status_code == 403, r.status_code
    assert _cuantas(uid_mio) == 0, "le ha abierto un chat a un cliente ajeno"


def test_no_se_abre_una_conversacion_con_uno_mismo(client, seed, admin_headers):
    """Una fila en la lista que no lleva a nadie."""
    suf = uuid.uuid4().hex[:8]
    uid_coach, h_coach, _uid_cli, _h = _monta(client, admin_headers, suf)
    r = _con(client, h_coach, uid_coach)
    assert r.status_code == 400, r.status_code


def test_un_usuario_que_no_existe_se_dice(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    _uc, h_coach, _uid, _h = _monta(client, admin_headers, suf)
    assert _con(client, h_coach, 999999).status_code == 404


def test_el_cliente_tampoco_le_abre_chat_a_quien_quiera(client, seed, admin_headers):
    """Vale para todos, no solo para los coaches."""
    suf = uuid.uuid4().hex[:8]
    _u1, _h1, _uid_mio, h_cli = _monta(client, admin_headers, suf, "x")
    _u2, _h2, uid_ajeno, _h3 = _monta(client, admin_headers, suf, "y")

    r = _con(client, h_cli, uid_ajeno)
    assert r.status_code == 403, r.status_code
