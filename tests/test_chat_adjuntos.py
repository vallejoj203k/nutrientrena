"""Adjuntos en el chat: mandar una foto o el PDF de la dieta.

Hasta ahora un mensaje solo podía ser texto, y el coach que quería mandarle una
foto a su cliente tenía que salirse a WhatsApp.

Dos cosas que conviene tener escritas:

  · Un mensaje puede ser SOLO un archivo, sin texto. Obligar a escribir algo
    para poder mandar una foto es pedir relleno.
  · Pero no puede ser NADA: sin esa comprobación, darle a Enviar en blanco
    dejaba una burbuja vacía en la conversación de los dos, y ninguno de los
    dos sabía si se había perdido un mensaje.

La subida vive en `/chat/conversations/{id}/attachment` y no en el subidor
general a propósito: el permiso que hace falta es "estar en esta conversación",
y eso el subidor general no lo comprueba.
"""
import io
import uuid

from tests.test_chat_grupos import _cliente_de
from tests.test_org_scope import _crear_coach, _crear_usuario

FOTO = ("foto.png", io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"0" * 40), "image/png")


def _monta(client, admin_headers, suf):
    """Un coach, un cliente suyo, y la conversación entre los dos."""
    _uid, det_coach, h_coach = _crear_coach(
        client, admin_headers, f"coach.adj.{suf}@nutrientrena-qa.com")
    det_cli, h_cli = _cliente_de(
        client, admin_headers, det_coach, f"cli.adj.{suf}@nutrientrena-qa.com")

    from app.database import SessionLocal
    from app.models.user import UserDetail
    db = SessionLocal()
    try:
        uid_cli = db.query(UserDetail).filter(UserDetail.id == det_cli).first().user_id
    finally:
        db.close()

    r = client.post("/api/chat/conversations", headers=h_coach,
                    json={"type": "individual", "participant_user_ids": [uid_cli]})
    assert r.status_code == 200, r.text
    return h_coach, h_cli, r.json()["data"]["id"]


def _mandar(client, headers, conv, **cuerpo):
    return client.post(f"/api/chat/conversations/{conv}/messages", headers=headers, json=cuerpo)


def _mensajes(client, headers, conv):
    r = client.get(f"/api/chat/conversations/{conv}/messages", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()["data"]["messages"]


# ── Un mensaje que es solo un archivo ──────────────────────────────────────

def test_UN_MENSAJE_PUEDE_SER_SOLO_UN_ARCHIVO(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    h_coach, h_cli, conv = _monta(client, admin_headers, suf)

    r = _mandar(client, h_coach, conv,
                attachment_url="https://cdn.example/chat/dieta.pdf",
                attachment_name="dieta-julio.pdf",
                attachment_type="application/pdf", attachment_size=204800)
    assert r.status_code == 200, r.text

    # Y le llega al cliente con lo necesario para enseñarlo: el nombre de
    # verdad y el tipo, no solo una URL con un uuid dentro.
    m = _mensajes(client, h_cli, conv)[-1]
    assert m["attachment_url"].endswith("dieta.pdf"), m
    assert m["attachment_name"] == "dieta-julio.pdf", m
    assert m["attachment_type"] == "application/pdf", m
    assert m["attachment_size"] == 204800, m
    assert not (m["content"] or ""), m


def test_y_puede_llevar_texto_de_pie_de_foto(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    h_coach, h_cli, conv = _monta(client, admin_headers, suf)
    _mandar(client, h_coach, conv, content="Aquí tienes la dieta",
            attachment_url="https://cdn.example/chat/d.pdf",
            attachment_name="d.pdf", attachment_type="application/pdf")

    m = _mensajes(client, h_cli, conv)[-1]
    assert m["content"] == "Aquí tienes la dieta", m
    assert m["attachment_name"] == "d.pdf", m


def test_UN_MENSAJE_VACIO_DEL_TODO_NO_SE_GUARDA(client, seed, admin_headers):
    """Sin esto, darle a Enviar sin escribir nada dejaba una burbuja en blanco
    en la conversación de los dos."""
    suf = uuid.uuid4().hex[:8]
    h_coach, _h_cli, conv = _monta(client, admin_headers, suf)

    assert _mandar(client, h_coach, conv).status_code == 422
    assert _mandar(client, h_coach, conv, content="   ").status_code == 422
    assert _mensajes(client, h_coach, conv) == []


def test_el_texto_a_secas_sigue_funcionando(client, seed, admin_headers):
    """Lo de siempre no se rompe por añadir adjuntos."""
    suf = uuid.uuid4().hex[:8]
    h_coach, h_cli, conv = _monta(client, admin_headers, suf)
    assert _mandar(client, h_coach, conv, content="Hola").status_code == 200

    m = _mensajes(client, h_cli, conv)[-1]
    assert m["content"] == "Hola" and m["attachment_url"] is None, m


# ── Quién puede subir ──────────────────────────────────────────────────────

def test_NO_SE_PUEDE_SUBIR_A_UNA_CONVERSACION_AJENA(client, seed, admin_headers):
    """El permiso es "estar en esta conversación". Sin comprobarlo, cualquiera
    con cuenta podría dejar archivos en la carpeta de una conversación de otros.
    """
    suf = uuid.uuid4().hex[:8]
    _h_coach, _h_cli, conv = _monta(client, admin_headers, suf)
    _u, _d, h_fuera = _crear_usuario(
        client, admin_headers, f"fuera.adj.{suf}@nutrientrena-qa.com", role_id=6)

    r = client.post(f"/api/chat/conversations/{conv}/attachment",
                    headers=h_fuera, files={"file": FOTO})
    assert r.status_code == 404, r.text


def test_tampoco_se_puede_mandar_un_mensaje_a_una_conversacion_ajena(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    _h_coach, _h_cli, conv = _monta(client, admin_headers, suf)
    _u, _d, h_fuera = _crear_usuario(
        client, admin_headers, f"fuera2.adj.{suf}@nutrientrena-qa.com", role_id=6)

    r = _mandar(client, h_fuera, conv, content="hola",
                attachment_url="https://cdn.example/x.pdf")
    assert r.status_code == 404, r.text


def test_un_tipo_de_archivo_que_no_toca_se_rechaza(client, seed, admin_headers):
    """Imágenes y PDF. Un .exe o un .zip en el chat no es lo que nadie quiere
    mandarle a su cliente, y sí es lo que a nadie le apetece alojar."""
    suf = uuid.uuid4().hex[:8]
    h_coach, _h_cli, conv = _monta(client, admin_headers, suf)

    r = client.post(f"/api/chat/conversations/{conv}/attachment", headers=h_coach,
                    files={"file": ("x.exe", io.BytesIO(b"MZ" + b"0" * 20),
                                    "application/x-msdownload")})
    assert r.status_code == 400, r.text
    assert "PDF" in r.json().get("message", "") or "imágenes" in r.json().get("message", "").lower()


# ── Lo que la lista de conversaciones enseña ───────────────────────────────

def test_la_lista_ve_el_ultimo_mensaje_aunque_sea_solo_un_archivo(client, seed, admin_headers):
    """La pantalla pone "📎 nombre" cuando no hay texto. Si el último mensaje
    no llegara, pondría "Sin mensajes" en una conversación que sí tiene uno."""
    suf = uuid.uuid4().hex[:8]
    h_coach, _h_cli, conv = _monta(client, admin_headers, suf)
    _mandar(client, h_coach, conv, attachment_url="https://cdn.example/f.png",
            attachment_name="progreso.png", attachment_type="image/png")

    convs = client.get("/api/chat/conversations", headers=h_coach).json()["data"]
    esta = [c for c in convs if c["id"] == conv][0]
    assert esta["last_message"]["attachment_name"] == "progreso.png", esta["last_message"]
