"""Borrar alimentos y comidas de una dieta tiene que persistir.

Bug reportado: en diets.html se elimina un alimento, se guarda, y al reabrir
la dieta el alimento sigue ahí.

Causa: el borrado en el editor es "por omisión" — la fila desaparece del
estado local y simplemente deja de enviarse. El backend sí podaba las filas
que dejaban de llegar, pero SOLO dentro de las comidas que recibía. Y el
frontend descarta del payload las comidas que se quedan sin alimentos
(`filter(f => f.detail.length > 0)`), así que al borrar el último alimento de
una comida, esa comida entera no se enviaba, nunca se visitaba, y ni ella ni
sus alimentos se tocaban en la base de datos.

Por lo mismo, eliminar una comida completa tampoco se guardaba.
"""
from app.database import SessionLocal
from app.models.nutrition.aliment import Aliment
from app.models.nutrition.diet import DietFood, DietFoodAliment


def _alimento(db, name, kcal=100.0):
    a = Aliment(name=name, calories=kcal, proteins=10, carbohydrates=10, fats=1)
    db.add(a)
    db.commit()
    db.refresh(a)
    return a.id


def _dieta_con_comidas(client, headers, titulo, comidas):
    """comidas = [(nombre, [aliment_id, ...]), ...]"""
    r = client.post("/api/diets", headers=headers, json={
        "title": titulo,
        "foods": [
            {"name": nombre, "time": "08:00",
             "detail": [{"aliment_id": aid, "quantity_calc": 100, "order": i}
                        for i, aid in enumerate(aids)]}
            for nombre, aids in comidas
        ],
    })
    assert r.status_code == 200, r.text
    return r.json()["data"]["id"]


def _leer(client, headers, diet_id):
    r = client.get(f"/api/diets/{diet_id}/edit", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()["data"]


def _contar_en_bd(diet_id):
    db = SessionLocal()
    try:
        comidas = db.query(DietFood).filter(DietFood.diet_id == diet_id).count()
        alimentos = db.query(DietFoodAliment).filter(DietFoodAliment.diet_id == diet_id).count()
        return comidas, alimentos
    finally:
        db.close()


def test_borrar_un_alimento_de_una_comida_con_varios(client, seed, admin_headers):
    """Este caso ya funcionaba: la comida se sigue enviando."""
    db = SessionLocal()
    try:
        a1, a2 = _alimento(db, "Arroz basmati"), _alimento(db, "Pollo")
    finally:
        db.close()

    diet_id = _dieta_con_comidas(client, admin_headers, "Dieta con comida de dos", [("Comida", [a1, a2])])
    datos = _leer(client, admin_headers, diet_id)
    comida = datos["foods"][0]
    queda = [d for d in comida["detail"] if d["aliment"]["name"] != "Pollo"]

    r = client.put(f"/api/diets/{diet_id}/update", headers=admin_headers, json={
        "id": diet_id, "title": datos["title"],
        "foods": [{"id": comida["id"], "name": comida["name"], "time": comida["time"],
                   "detail": [{"id": d["id"], "aliment_id": d["aliment"]["id"],
                               "quantity_calc": d["quantity"], "order": i}
                              for i, d in enumerate(queda)]}],
    })
    assert r.status_code == 200, r.text

    nombres = [d["aliment"]["name"] for d in _leer(client, admin_headers, diet_id)["foods"][0]["detail"]]
    assert nombres == ["Arroz basmati"], nombres


def test_borrar_el_ultimo_alimento_de_una_comida(client, seed, admin_headers):
    """El bug reportado: la comida se queda vacía, el frontend deja de
    enviarla, y antes eso significaba que no se borraba nada."""
    db = SessionLocal()
    try:
        a1, a2 = _alimento(db, "Aceite de almendra"), _alimento(db, "Lentejas")
    finally:
        db.close()

    diet_id = _dieta_con_comidas(client, admin_headers, "Dieta con comida de uno", [
        ("Desayuno", [a2]),
        ("Comida", [a1]),   # esta se queda vacía al borrar su único alimento
    ])
    datos = _leer(client, admin_headers, diet_id)
    desayuno = next(f for f in datos["foods"] if f["name"] == "Desayuno")

    # Exactamente lo que manda diets.html: la comida vacía no viaja
    r = client.put(f"/api/diets/{diet_id}/update", headers=admin_headers, json={
        "id": diet_id, "title": datos["title"],
        "foods": [{"id": desayuno["id"], "name": desayuno["name"], "time": desayuno["time"],
                   "detail": [{"id": d["id"], "aliment_id": d["aliment"]["id"],
                               "quantity_calc": d["quantity"], "order": i}
                              for i, d in enumerate(desayuno["detail"])]}],
    })
    assert r.status_code == 200, r.text

    foods = _leer(client, admin_headers, diet_id)["foods"]
    assert [f["name"] for f in foods] == ["Desayuno"], foods

    # Y no quedan filas huérfanas en la base
    comidas, alimentos = _contar_en_bd(diet_id)
    assert (comidas, alimentos) == (1, 1), (comidas, alimentos)


def test_una_comida_existente_puede_quedarse_vacia(client, seed, admin_headers):
    """Lo que manda diets.html tras el arreglo: la comida se sigue enviando,
    ya sin alimentos, porque es lo que el editor enseña en pantalla."""
    db = SessionLocal()
    try:
        a1 = _alimento(db, "Aceite de oliva")
    finally:
        db.close()

    diet_id = _dieta_con_comidas(client, admin_headers, "Dieta con comida vaciada", [("Comida", [a1])])
    datos = _leer(client, admin_headers, diet_id)
    comida = datos["foods"][0]

    r = client.put(f"/api/diets/{diet_id}/update", headers=admin_headers, json={
        "id": diet_id, "title": datos["title"],
        "foods": [{"id": comida["id"], "name": comida["name"], "time": comida["time"], "detail": []}],
    })
    assert r.status_code == 200, r.text

    foods = _leer(client, admin_headers, diet_id)["foods"]
    assert [f["name"] for f in foods] == ["Comida"]
    assert foods[0]["detail"] == []
    assert _contar_en_bd(diet_id) == (1, 0)


def test_eliminar_una_comida_entera(client, seed, admin_headers):
    """removeMeal() también borra por omisión."""
    db = SessionLocal()
    try:
        a1, a2 = _alimento(db, "Huevo entero"), _alimento(db, "Avena")
    finally:
        db.close()

    diet_id = _dieta_con_comidas(client, admin_headers, "Dieta a la que se le quita la cena", [
        ("Desayuno", [a1]),
        ("Cena", [a2]),
    ])
    datos = _leer(client, admin_headers, diet_id)
    desayuno = next(f for f in datos["foods"] if f["name"] == "Desayuno")

    r = client.put(f"/api/diets/{diet_id}/update", headers=admin_headers, json={
        "id": diet_id, "title": datos["title"],
        "foods": [{"id": desayuno["id"], "name": desayuno["name"], "time": desayuno["time"],
                   "detail": [{"id": d["id"], "aliment_id": d["aliment"]["id"],
                               "quantity_calc": d["quantity"], "order": i}
                              for i, d in enumerate(desayuno["detail"])]}],
    })
    assert r.status_code == 200, r.text
    assert [f["name"] for f in _leer(client, admin_headers, diet_id)["foods"]] == ["Desayuno"]


def test_vaciar_la_dieta_entera(client, seed, admin_headers):
    db = SessionLocal()
    try:
        a1 = _alimento(db, "Pan integral")
    finally:
        db.close()

    diet_id = _dieta_con_comidas(client, admin_headers, "Dieta que se vacía", [("Comida", [a1])])
    r = client.put(f"/api/diets/{diet_id}/update", headers=admin_headers, json={
        "id": diet_id, "title": "Dieta que se vacía", "foods": []})
    assert r.status_code == 200, r.text

    assert _leer(client, admin_headers, diet_id)["foods"] == []
    assert _contar_en_bd(diet_id) == (0, 0)


def test_las_comidas_nuevas_se_crean_en_orden_con_ids_ascendentes(client, seed, admin_headers):
    """Contrato del que depende el autoguardado de diets.html.

    Tras guardar, el editor tiene que asignar a cada comida y alimento nuevo su
    id de base de datos; si no, el siguiente autoguardado los mandaría otra vez
    sin id y se crearían duplicados. El emparejamiento se apoya en que lo nuevo
    se crea en el orden en que se envía y los ids son ascendentes. Si esto
    cambiara, el autoguardado empezaría a duplicar en silencio.
    """
    db = SessionLocal()
    try:
        a1, a2, a3 = _alimento(db, "Kéfir"), _alimento(db, "Nueces"), _alimento(db, "Manzana")
    finally:
        db.close()

    diet_id = _dieta_con_comidas(client, admin_headers, "Dieta que crece", [("Desayuno", [a1])])
    datos = _leer(client, admin_headers, diet_id)
    desayuno = datos["foods"][0]

    # Se añaden dos comidas nuevas (sin id) en un orden concreto
    r = client.put(f"/api/diets/{diet_id}/update", headers=admin_headers, json={
        "id": diet_id, "title": datos["title"],
        "foods": [
            {"id": desayuno["id"], "name": "Desayuno", "time": "08:00",
             "detail": [{"id": d["id"], "aliment_id": d["aliment"]["id"],
                         "quantity_calc": d["quantity"], "order": 0} for d in desayuno["detail"]]},
            {"name": "Merienda", "time": "17:00",
             "detail": [{"aliment_id": a2, "quantity_calc": 30, "order": 0}]},
            {"name": "Cena", "time": "21:00",
             "detail": [{"aliment_id": a3, "quantity_calc": 150, "order": 0}]},
        ],
    })
    assert r.status_code == 200, r.text

    foods = _leer(client, admin_headers, diet_id)["foods"]
    nuevas = [f for f in foods if f["id"] != desayuno["id"]]
    # Ordenadas por id ascendente, salen en el orden en que se enviaron
    nuevas.sort(key=lambda f: f["id"])
    assert [f["name"] for f in nuevas] == ["Merienda", "Cena"], nuevas


def test_no_mandar_foods_no_borra_nada(client, seed, admin_headers):
    """Regresión importante: si el cliente no manda `foods` en absoluto (una
    edición parcial, por ejemplo solo el título), las comidas se quedan como
    están. Sin esto, la poda vaciaría la dieta entera."""
    db = SessionLocal()
    try:
        a1 = _alimento(db, "Salmón")
    finally:
        db.close()

    diet_id = _dieta_con_comidas(client, admin_headers, "Dieta a la que solo se cambia el título",
                                 [("Cena", [a1])])

    r = client.put(f"/api/diets/{diet_id}/update", headers=admin_headers, json={
        "id": diet_id, "title": "Título nuevo"})
    assert r.status_code == 200, r.text

    datos = _leer(client, admin_headers, diet_id)
    assert datos["title"] == "Título nuevo"
    assert [f["name"] for f in datos["foods"]] == ["Cena"], datos["foods"]
