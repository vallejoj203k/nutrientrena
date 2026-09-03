"""Lo que suma un menú entero, micronutrientes incluidos.

El constructor de dietas enseña kcal y macros mientras se monta el plan, pero
los micronutrientes no salían por ninguna parte: para saber si un día llega al
hierro había que abrir alimento por alimento y sumar a mano.

La suma se hace en el servidor porque los micros no viajan con la dieta —son
treinta números por alimento— y se pide con las cantidades que hay puestas en
ese momento, así que vale también para una dieta sin guardar.

Lo que hay que dejar sujeto:

  · Que sume de verdad, respetando la porción de cada alimento.
  · Que un micronutriente que nadie registra NO salga: no es cero, es que no
    se sabe, y un cero se lee como un dato.
  · Que diga cuántos alimentos no aportan ficha, porque si no la suma parece
    completa cuando está coja.
"""
import uuid

from tests.test_macros_porcion import _monta


def _alimento(client, h, nombre, micros=None, **campos):
    body = {"name": nombre, "calories": 100, "proteins": 10, "carbohydrates": 5,
            "fats": 2, "quantity": 100, "quantity_unit": "g"}
    body.update(campos)
    if micros:
        body["description"] = micros
    r = client.post("/api/aliments", headers=h, json=body)
    assert r.status_code == 200, r.text
    return r.json()["data"]["id"]


def _resumen(client, h, items):
    r = client.post("/api/aliments/resumen-nutricional", headers=h, json={"items": items})
    assert r.status_code == 200, r.text
    return r.json()["data"]


# ── La suma ────────────────────────────────────────────────────────────────

def test_SUMA_LOS_MICROS_DE_TODO_EL_MENU(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    h, _det, _hc = _monta(client, admin_headers, suf)
    a = _alimento(client, h, f"Lenteja {suf}", {"iron": 4.0, "fiber": 8.0})
    b = _alimento(client, h, f"Espinaca {suf}", {"iron": 2.0, "vitc": 30.0})

    d = _resumen(client, h, [{"aliment_id": a, "quantity": 100},
                             {"aliment_id": b, "quantity": 100}])
    assert d["micros"]["iron"] == 6.0, d["micros"]
    assert d["micros"]["fiber"] == 8.0, d["micros"]
    assert d["micros"]["vitc"] == 30.0, d["micros"]


def test_y_los_macros_del_menu(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    h, _det, _hc = _monta(client, admin_headers, suf)
    a = _alimento(client, h, f"Pollo {suf}", calories=165, proteins=31)

    d = _resumen(client, h, [{"aliment_id": a, "quantity": 200}])
    assert d["calories"] == 330.0, d
    assert d["proteins"] == 62.0, d


def test_LA_CANTIDAD_MANDA(client, seed, admin_headers):
    """200 g de lentejas llevan el doble de hierro que 100."""
    suf = uuid.uuid4().hex[:8]
    h, _det, _hc = _monta(client, admin_headers, suf)
    a = _alimento(client, h, f"Lenteja {suf}", {"iron": 4.0})

    assert _resumen(client, h, [{"aliment_id": a, "quantity": 200}])["micros"]["iron"] == 8.0
    assert _resumen(client, h, [{"aliment_id": a, "quantity": 50}])["micros"]["iron"] == 2.0


def test_RESPETA_LA_PORCION_DEL_ALIMENTO(client, seed, admin_headers):
    """Un huevo trae sus micros por UNIDAD, no por 100 g: dos huevos son dos
    veces su hierro, no la centésima parte."""
    suf = uuid.uuid4().hex[:8]
    h, _det, _hc = _monta(client, admin_headers, suf)
    huevo = _alimento(client, h, f"Huevo {suf}", {"iron": 0.9},
                      quantity=1, quantity_unit="ud", calories=74)

    d = _resumen(client, h, [{"aliment_id": huevo, "quantity": 2}])
    assert d["micros"]["iron"] == 1.8, d["micros"]
    assert d["calories"] == 148.0, d


def test_el_mismo_alimento_en_dos_comidas_se_suma(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    h, _det, _hc = _monta(client, admin_headers, suf)
    a = _alimento(client, h, f"Avena {suf}", {"fiber": 10.0})

    d = _resumen(client, h, [{"aliment_id": a, "quantity": 50},
                             {"aliment_id": a, "quantity": 50}])
    assert d["micros"]["fiber"] == 10.0, d["micros"]


# ── Lo que no se sabe, no se inventa ───────────────────────────────────────

def test_UN_MICRO_QUE_NADIE_REGISTRA_NO_SALE(client, seed, admin_headers):
    """Un cero se lee como un dato: "este menú no tiene nada de zinc". Y lo
    que pasa es que no se sabe."""
    suf = uuid.uuid4().hex[:8]
    h, _det, _hc = _monta(client, admin_headers, suf)
    a = _alimento(client, h, f"Lenteja {suf}", {"iron": 4.0})

    d = _resumen(client, h, [{"aliment_id": a, "quantity": 100}])
    assert "iron" in d["micros"]
    assert "zinc" not in d["micros"], d["micros"]
    assert "vitc" not in d["micros"], d["micros"]


def test_DICE_CUANTOS_ALIMENTOS_NO_APORTAN_FICHA(client, seed, admin_headers):
    """Si la mitad del plan no tiene micros, la suma se queda corta y hay que
    decirlo: si no, un total incompleto parece completo."""
    suf = uuid.uuid4().hex[:8]
    h, _det, _hc = _monta(client, admin_headers, suf)
    con = _alimento(client, h, f"Lenteja {suf}", {"iron": 4.0})
    sin1 = _alimento(client, h, f"Agua {suf}")
    sin2 = _alimento(client, h, f"Sal {suf}")

    d = _resumen(client, h, [{"aliment_id": con, "quantity": 100},
                             {"aliment_id": sin1, "quantity": 100},
                             {"aliment_id": sin2, "quantity": 5}])
    assert d["con_datos"] == 1, d
    assert d["sin_datos"] == 2, d


def test_el_indice_glucemico_no_se_suma(client, seed, admin_headers):
    """No es una cantidad: sumar tres índices glucémicos no significa nada."""
    suf = uuid.uuid4().hex[:8]
    h, _det, _hc = _monta(client, admin_headers, suf)
    a = _alimento(client, h, f"Pan {suf}", {"glycemic_index": 70, "iron": 1.0})
    b = _alimento(client, h, f"Arroz {suf}", {"glycemic_index": 73})

    d = _resumen(client, h, [{"aliment_id": a, "quantity": 100},
                             {"aliment_id": b, "quantity": 100}])
    assert "glycemic_index" not in d["micros"], d["micros"]
    assert d["micros"]["iron"] == 1.0


# ── Casos que se dan ───────────────────────────────────────────────────────

def test_un_plan_vacio_da_ceros_sin_reventar(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    h, _det, _hc = _monta(client, admin_headers, suf)
    d = _resumen(client, h, [])
    assert d["calories"] == 0 and d["micros"] == {}


def test_una_cantidad_a_cero_no_aporta(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    h, _det, _hc = _monta(client, admin_headers, suf)
    a = _alimento(client, h, f"Lenteja {suf}", {"iron": 4.0})
    d = _resumen(client, h, [{"aliment_id": a, "quantity": 0}])
    assert d["micros"] == {}, d["micros"]


def test_un_alimento_que_ya_no_existe_se_dice(client, seed, admin_headers):
    """Pasa con una dieta cuyo alimento se borró del catálogo: se avisa en vez
    de sumar como si nada."""
    suf = uuid.uuid4().hex[:8]
    h, _det, _hc = _monta(client, admin_headers, suf)
    a = _alimento(client, h, f"Lenteja {suf}", {"iron": 4.0})
    fantasma = str(uuid.uuid4())

    d = _resumen(client, h, [{"aliment_id": a, "quantity": 100},
                             {"aliment_id": fantasma, "quantity": 100}])
    assert d["no_encontrados"] == [fantasma], d
    assert d["micros"]["iron"] == 4.0


def test_LA_COPIA_DE_LA_DIETA_TAMBIEN_SUMA(client, seed, admin_headers):
    """El plan guardado no apunta al alimento del catálogo, sino a una copia
    suya. Si la copia no contara, el resumen de una dieta ya guardada saldría
    vacío."""
    suf = uuid.uuid4().hex[:8]
    h, _det, _hc = _monta(client, admin_headers, suf)
    original = _alimento(client, h, f"Lenteja {suf}", {"iron": 4.0})
    r = client.post("/api/diets", headers=h, json={
        "title": f"Dieta {suf}",
        "foods": [{"name": "Comida", "time": "14:00", "detail": [
            {"aliment_id": original, "quantity_calc": 100, "order": 0}]}]})
    assert r.status_code == 200, r.text
    copia = r.json()["data"]["foods"][0]["detail"][0]["aliment_id"]
    assert copia != original

    d = _resumen(client, h, [{"aliment_id": copia, "quantity": 100}])
    assert d["micros"]["iron"] == 4.0, d["micros"]
