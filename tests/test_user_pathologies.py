"""Las patologías del cliente se guardan, se devuelven y filtran la dieta."""


def _pathology_ids(client, h, *nombres):
    r = client.get("/api/pathologies/findAll", headers=h)
    assert r.status_code == 200, r.text
    catalogo = {p["name"]: p["id"] for p in r.json()["data"]}
    return [catalogo[n] for n in nombres if n in catalogo], catalogo


def test_crear_cliente_con_patologias(client, seed, admin_headers, db):
    h = admin_headers
    from app.models.nutrition.diet import Pathology
    # Lo que falte, por nombre: con "solo si la tabla está vacía" bastaba con
    # que otra prueba sembrara antes para quedarse sin las suyas.
    hay = {p.name for p in db.query(Pathology).all()}
    faltan = [Pathology(name=n) for n in ("Enfermedad celíaca", "Intolerancia a la lactosa")
              if n not in hay]
    if faltan:
        db.add_all(faltan)
        db.commit()

    ids, catalogo = _pathology_ids(client, h, "Enfermedad celíaca")
    assert ids, catalogo

    r = client.post("/api/users", headers=h, json={
        "name": "Ana", "last_name": "Celíaca", "email": "ana.celiaca@test.com",
        "password": "Secreta123!", "role_id": 6, "pathology_ids": ids,
    })
    assert r.status_code == 200, r.text
    detail_id = r.json()["data"]["id"]

    # Se devuelve en la ficha
    r2 = client.get(f"/api/users/{detail_id}/edit", headers=h)
    assert r2.status_code == 200, r2.text
    nombres = [p["name"] for p in r2.json()["data"]["pathologies"]]
    assert "Enfermedad celíaca" in nombres, nombres


def test_actualizar_reemplaza_las_patologias(client, seed, admin_headers):
    h = admin_headers
    ids_cel, catalogo = _pathology_ids(client, h, "Enfermedad celíaca")
    ids_lac, _ = _pathology_ids(client, h, "Intolerancia a la lactosa")

    r = client.post("/api/users", headers=h, json={
        "name": "Luis", "email": "luis.patos@test.com", "password": "Secreta123!",
        "role_id": 6, "pathology_ids": ids_cel})
    detail_id = r.json()["data"]["id"]

    r2 = client.put(f"/api/users/{detail_id}/update", headers=h,
                    json={"pathology_ids": ids_lac})
    assert r2.status_code == 200, r2.text
    nombres = [p["name"] for p in r2.json()["data"]["pathologies"]]
    assert nombres == ["Intolerancia a la lactosa"], nombres

    # Y se pueden quitar todas
    r3 = client.put(f"/api/users/{detail_id}/update", headers=h, json={"pathology_ids": []})
    assert r3.json()["data"]["pathologies"] == []


def test_la_dieta_generada_excluye_lo_que_prohibe_la_patologia(client, seed, admin_headers):
    h = admin_headers
    for nombre, k, p, c, f in [
        ("Pan integral", 247, 9, 41, 3), ("Arroz integral", 355, 7, 74, 3),
        ("Pechuga de pollo", 110, 23, 0, 2), ("Aceite de oliva", 884, 0, 0, 100),
        ("Patata", 77, 2, 17, 0.1),
    ]:
        client.post("/api/aliments", headers=h, json={
            "name": nombre, "calories": k, "proteins": p, "carbohydrates": c, "fats": f})

    ids, _ = _pathology_ids(client, h, "Enfermedad celíaca")
    r = client.post("/api/users", headers=h, json={
        "name": "Marta", "email": "marta.celiaca@test.com", "password": "Secreta123!",
        "role_id": 6, "pathology_ids": ids})
    detail_id = r.json()["data"]["id"]

    r2 = client.post("/api/diets/auto-generate", headers=h, json={
        "client_id": detail_id, "kcal": 2000, "proteins": 150, "carbs": 200,
        "fats": 60, "meal_count": 3})
    assert r2.status_code == 200, r2.text
    nombres = [f["name"] for m in r2.json()["data"]["foods"] for f in m["detail"]]
    assert not any("Pan" in n for n in nombres), nombres
    assert nombres, "debería seguir construyendo un plan"

    # El aviso viaja en la respuesta y en las notas de la dieta
    d = r2.json()["data"]
    assert d["warnings"] and d["warnings"][0]["applied"] is True
    assert "Enfermedad celíaca" in d["notes"]
