"""Lo que crea un coach en su librería es SUYO hasta que Alzum lo suba.

Esa es la regla, y es la que está implementada: se comprueba aquí de las dos
maneras —que otro centro no lo ve antes, y que sí lo ve después de subirlo—.
Subirlo desde «Contenido de organizaciones» es la única puerta.

Queda un hueco anotado abajo, que NO se llega a él por la aplicación: hace
falta crear un coach llamando a la API directamente, saltándose el panel. El
alta del panel siempre le crea su centro.
"""
import uuid

import pytest

from app.database import SessionLocal
from app.models.training import Training

from tests.test_org_scope import _crear_coach, _crear_organizacion


def _coach_con_centro(client, admin_headers, suf, nombre="con"):
    _uid, det, h = _crear_coach(client, admin_headers, f"{nombre}.priv.{suf}@nutrientrena-qa.com")
    _crear_organizacion(det, f"Centro {nombre} {suf}")
    return h


def _coach_sin_centro(client, admin_headers, suf):
    """Un coach al que NADIE le ha creado organización."""
    _uid, _det, h = _crear_coach(client, admin_headers, f"sin.priv.{suf}@nutrientrena-qa.com")
    return h


def _busca(client, headers, texto):
    r = client.get(f"/api/trainings/search?search={texto}", headers=headers)
    assert r.status_code == 200, r.text
    datos = r.json()["data"]
    return datos.get("data", datos) if isinstance(datos, dict) else datos


def _ambito(client, headers, id_):
    """Qué organization_id tiene la pieza, según la ve quien pregunta."""
    db = SessionLocal()
    try:
        t = db.query(Training).filter(Training.id == id_).first()
        return t.organization_id if t else "no existe"
    finally:
        db.close()


def test_lo_de_un_coach_con_centro_no_lo_ve_otro_centro(client, seed, admin_headers):
    """El caso normal, para tener con qué comparar."""
    suf = uuid.uuid4().hex[:8]
    h_a = _coach_con_centro(client, admin_headers, suf, "a")
    h_b = _coach_con_centro(client, admin_headers, suf, "b")

    ej = client.post("/api/trainings", headers=h_a,
                     json={"name": f"Privado A {suf}"}).json()["data"]
    assert _ambito(client, h_a, ej["id"]) is not None, "debería nacer en su organización"

    assert any(f["id"] == ej["id"] for f in _busca(client, h_a, suf)), "el suyo sí lo ve"
    assert not any(f["id"] == ej["id"] for f in _busca(client, h_b, suf)), "el otro NO"


@pytest.mark.xfail(strict=True, reason=(
    "Hueco conocido, no alcanzable desde la aplicación. Un coach dado de alta "
    "por API sin centro crea con organization_id NULL, que es la marca del "
    "catálogo de Alzum, así que su librería se ve desde otras cuentas. "
    "Cerrarlo bien pide distinguir 'es de la plataforma' de 'no tiene centro', "
    "y hoy las dos cosas se escriben igual: NULL. Hace falta una columna que "
    "lo diga, o garantizar que todo coach tenga centro — y eso último cambia "
    "quién es dueño de qué. Decisión pendiente del cliente."))
def test_UN_COACH_SIN_CENTRO_no_publica_su_libreria_sin_querer(client, seed, admin_headers):
    """El hueco, escrito para que se entere solo el día que se cierre.

    Si su ejercicio nace con organization_id NULL, cualquier otra cuenta lo ve
    en su Librería sin que Alzum lo haya subido a nada.
    """
    suf = uuid.uuid4().hex[:8]
    h_sin = _coach_sin_centro(client, admin_headers, suf)
    h_otro = _coach_con_centro(client, admin_headers, suf, "otro")

    ej = client.post("/api/trainings", headers=h_sin,
                     json={"name": f"Privado sin centro {suf}"}).json()["data"]

    ambito = _ambito(client, h_sin, ej["id"])
    visto_por_otro = any(f["id"] == ej["id"] for f in _busca(client, h_otro, suf))

    assert not visto_por_otro, (
        f"Su librería se ve desde otra cuenta sin que nadie la haya subido. "
        f"organization_id = {ambito!r}")


def test_solo_se_vuelve_comun_cuando_alzum_lo_sube(client, seed, admin_headers):
    """La regla, dicha entera: antes de subirlo no lo ve nadie más; después,
    sí. Es la única puerta."""
    suf = uuid.uuid4().hex[:8]
    h_a = _coach_con_centro(client, admin_headers, suf, "a")
    h_b = _coach_con_centro(client, admin_headers, suf, "b")

    ej = client.post("/api/trainings", headers=h_a,
                     json={"name": f"Se sube {suf}"}).json()["data"]
    assert not any(f["id"] == ej["id"] for f in _busca(client, h_b, suf)), "antes, no"

    r = client.put(f"/api/content/training/{ej['id']}/organization",
                   headers=admin_headers, json={"organization_id": None})
    assert r.status_code == 200, r.text

    assert any(f["id"] == ej["id"] for f in _busca(client, h_b, suf)), "después, sí"
