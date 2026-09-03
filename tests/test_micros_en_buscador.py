"""Los micronutrientes viajan con el alimento al buscador de la dieta.

El panel de "Buscar alimentos" los enseña al elegir un alimento, y los lee de
lo que devuelve la búsqueda. Si la ficha de micros no viniera en la respuesta,
el desplegable saldría vacío en todos los alimentos y no habría forma de verlo
desde la pantalla.
"""
import uuid

from tests.test_macros_porcion import _monta


def _alimento(client, h, nombre, micros=None):
    body = {"name": nombre, "calories": 165, "proteins": 31, "carbohydrates": 0,
            "fats": 3.6, "quantity": 100, "quantity_unit": "g"}
    if micros:
        body["description"] = micros
    r = client.post("/api/aliments", headers=h, json=body)
    assert r.status_code == 200, r.text
    return r.json()["data"]["id"]


def _buscar(client, h, texto):
    r = client.get(f"/api/aliments/search?search={texto}", headers=h)
    assert r.status_code == 200, r.text
    return r.json()["data"]["data"]


def test_LA_BUSQUEDA_TRAE_LA_FICHA_DE_MICROS(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    h, _det, _hc = _monta(client, admin_headers, suf)
    _alimento(client, h, f"Pechuga {suf}",
              {"vitb3": 13.7, "phosphorus": 210, "selenium": 22, "saturated_fats": 1.0})

    hallados = _buscar(client, h, f"Pechuga {suf}")
    assert hallados, "no sale en la búsqueda"
    ficha = hallados[0].get("description")
    assert ficha, "la búsqueda no trae los micronutrientes"
    assert ficha["vitb3"] == 13.7, ficha
    assert ficha["phosphorus"] == 210, ficha
    assert ficha["selenium"] == 22, ficha
    assert ficha["saturated_fats"] == 1.0, ficha


def test_un_alimento_sin_micros_no_trae_ficha(client, seed, admin_headers):
    """El panel se esconde cuando no hay nada; para eso tiene que poder
    distinguir "sin datos" de "no me los han mandado"."""
    suf = uuid.uuid4().hex[:8]
    h, _det, _hc = _monta(client, admin_headers, suf)
    _alimento(client, h, f"Agua {suf}")

    hallados = _buscar(client, h, f"Agua {suf}")
    assert hallados
    assert not hallados[0].get("description"), hallados[0].get("description")


def test_el_catalogo_completo_tambien(client, seed, admin_headers):
    """La biblioteca de alimentos lee del mismo sitio."""
    suf = uuid.uuid4().hex[:8]
    h, _det, _hc = _monta(client, admin_headers, suf)
    aid = _alimento(client, h, f"Lenteja {suf}", {"iron": 4.7})

    r = client.get("/api/aliments/findAll", headers=h)
    assert r.status_code == 200, r.text
    mio = [a for a in r.json()["data"] if a["id"] == aid]
    assert mio and mio[0]["description"]["iron"] == 4.7, mio
