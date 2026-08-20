"""De quién es cada ejercicio, aunque haya subido a la plataforma.

Subir contenido de una cuenta al catálogo común le cambia el ÁMBITO
(`organization_id` pasa a NULL), no la autoría: lo hizo quien lo hizo. Sin
decirlo, un ejercicio que creó un coach y la plataforma subió queda
indistinguible de los de fábrica, y no hay a quién preguntarle si algo está
mal.

`created_user_id` es lo único que sobrevive a la promoción, así que es de ahí
de donde sale el nombre.
"""
import uuid

from app.database import SessionLocal
from app.models.training import Training

from tests.test_org_scope import _crear_coach, _crear_organizacion


def _coach_con_centro(client, admin_headers, suf, nombre="Marta"):
    _uid, det, h = _crear_coach(client, admin_headers, f"{nombre.lower()}.{suf}@nutrientrena-qa.com")
    _crear_organizacion(det, f"Centro {nombre} {suf}")
    return h


def _busca(client, headers, texto):
    r = client.get(f"/api/trainings/search?search={texto}", headers=headers)
    assert r.status_code == 200, r.text
    datos = r.json()["data"]
    return datos.get("data", datos) if isinstance(datos, dict) else datos


def test_el_listado_dice_quien_creo_cada_ejercicio(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    h_coach = _coach_con_centro(client, admin_headers, suf)
    r = client.post("/api/trainings", headers=h_coach, json={"name": f"Sentadilla {suf}"})
    assert r.status_code == 200, r.text

    fila = _busca(client, h_coach, suf)[0]
    assert fila["created_by_name"], fila
    assert fila["created_user_id"], fila


def test_el_autor_sobrevive_a_subirlo_a_la_plataforma(client, seed, admin_headers):
    """Lo que se pidió: que se siga sabiendo de dónde salió."""
    suf = uuid.uuid4().hex[:8]
    h_coach = _coach_con_centro(client, admin_headers, suf)
    ej = client.post("/api/trainings", headers=h_coach,
                     json={"name": f"Sentadilla {suf}"}).json()["data"]
    autor_antes = _busca(client, h_coach, suf)[0]["created_by_name"]

    subir = client.put(f"/api/content/training/{ej['id']}/organization",
                       headers=admin_headers, json={"organization_id": None})
    assert subir.status_code == 200, subir.text

    # Ya es de la plataforma…
    fila = _busca(client, admin_headers, suf)[0]
    assert fila["organization_id"] is None, fila
    # …pero sigue diciendo quién lo hizo.
    assert fila["created_by_name"] == autor_antes, fila


def test_el_detalle_tambien_lo_dice(client, seed, admin_headers):
    """La ficha del ejercicio abre por otra ruta: si solo se hubiera arreglado
    el listado, al abrirlo se perdería el dato."""
    suf = uuid.uuid4().hex[:8]
    h_coach = _coach_con_centro(client, admin_headers, suf)
    ej = client.post("/api/trainings", headers=h_coach,
                     json={"name": f"Remo {suf}"}).json()["data"]

    r = client.get(f"/api/trainings/{ej['id']}/edit", headers=h_coach)
    assert r.status_code == 200, r.text
    assert r.json()["data"]["created_by_name"], r.json()["data"]


def test_un_ejercicio_de_fabrica_no_inventa_un_autor(client, seed, admin_headers):
    """El catálogo base no lo creó nadie en la aplicación: se deja vacío en vez
    de atribuírselo a quien lo importó."""
    suf = uuid.uuid4().hex[:8]
    db = SessionLocal()
    try:
        db.add(Training(name=f"Ejercicio de fábrica {suf}", state=1,
                        organization_id=None, created_user_id=None))
        db.commit()
    finally:
        db.close()

    fila = _busca(client, admin_headers, suf)[0]
    assert fila["created_by_name"] is None, fila


def test_el_nombre_sale_de_la_ficha_y_no_del_correo(client, seed, admin_headers):
    """Se enseña "Marta Ruiz", no "marta.a1b2@..."; es lo que un humano
    reconoce al mirar la tarjeta."""
    suf = uuid.uuid4().hex[:8]
    h_coach = _coach_con_centro(client, admin_headers, suf, nombre="Marta")
    client.post("/api/trainings", headers=h_coach, json={"name": f"Peso muerto {suf}"})

    fila = _busca(client, h_coach, suf)[0]
    assert "@" not in (fila["created_by_name"] or ""), fila
