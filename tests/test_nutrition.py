"""Tests for nutrition endpoints: aliments, type food, group food."""
import pytest


@pytest.fixture(scope="module")
def food_type_id(client, admin_headers):
    r = client.post("/api/typeFood", json={"name": "Proteína", "state": 1},
                    headers=admin_headers)
    assert r.status_code == 200
    return r.json()["data"]["id"]


@pytest.fixture(scope="module")
def group_food_id(client, admin_headers):
    r = client.post("/api/groupFood", json={"name": "Carnes", "state": 1},
                    headers=admin_headers)
    assert r.status_code == 200
    return r.json()["data"]["id"]


@pytest.fixture(scope="module")
def aliment_id(client, admin_headers, group_food_id):
    r = client.post("/api/aliments", json={
        "name": "Pechuga de pollo",
        "proteins": 31.0,
        "carbohydrates": 0.0,
        "fats": 3.6,
        "calories": 165.0,
        "group_food_id": group_food_id,
    }, headers=admin_headers)
    assert r.status_code == 200
    return r.json()["data"]["id"]


class TestTypeFoods:
    def test_create(self, client, admin_headers):
        r = client.post("/api/typeFood", json={"name": "Lácteos", "state": 1},
                        headers=admin_headers)
        assert r.status_code == 200
        assert r.json()["data"]["name"] == "Lácteos"

    def test_list(self, client, admin_headers):
        r = client.get("/api/typeFood/findAll", headers=admin_headers)
        assert r.status_code == 200
        assert isinstance(r.json()["data"], list)

    def test_requires_auth(self, client):
        r = client.get("/api/typeFood/findAll")
        assert r.status_code == 403


class TestGroupFoods:
    def test_create(self, client, admin_headers):
        r = client.post("/api/groupFood", json={"name": "Verduras", "state": 1},
                        headers=admin_headers)
        assert r.status_code == 200

    def test_list(self, client, admin_headers):
        r = client.get("/api/groupFood/findAll", headers=admin_headers)
        assert r.status_code == 200
        assert isinstance(r.json()["data"], list)


class TestAliments:
    def test_create(self, client, admin_headers, group_food_id):
        r = client.post("/api/aliments", json={
            "name": "Arroz blanco",
            "proteins": 2.7,
            "carbohydrates": 28.2,
            "fats": 0.3,
            "calories": 130.0,
            "group_food_id": group_food_id,
        }, headers=admin_headers)
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["name"] == "Arroz blanco"
        assert data["proteins"] == 2.7

    def test_macros_stored_correctly(self, client, admin_headers, aliment_id):
        r = client.get(f"/api/aliments/{aliment_id}/edit", headers=admin_headers)
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["proteins"] == 31.0
        assert data["fats"] == 3.6
        assert data["calories"] == 165.0

    def test_search(self, client, admin_headers):
        r = client.get("/api/aliments/search?search=pollo", headers=admin_headers)
        assert r.status_code == 200
        # search returns {"data": [...], "total": ..., "page": ..., "per_page": ...}
        results = r.json()["data"]["data"]
        assert any("pollo" in a["name"].lower() for a in results)

    def test_update(self, client, admin_headers, aliment_id):
        r = client.put(f"/api/aliments/{aliment_id}/update", json={"calories": 170.0},
                       headers=admin_headers)
        assert r.status_code == 200
        assert r.json()["data"]["calories"] == 170.0

    def test_requires_auth(self, client):
        r = client.get("/api/aliments/search?search=pollo")
        assert r.status_code == 403


class TestRecipes:
    def test_create_recipe(self, client, admin_headers, aliment_id):
        r = client.post("/api/recipes", json={
            "name": "Pollo al vapor",
            "description": "Simple y saludable",
            "details": [{"aliment_id": aliment_id, "quantity": 150, "order": 0}],
        }, headers=admin_headers)
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["name"] == "Pollo al vapor"
        # macros are stored separately via frontend calc; recipe row is created successfully
        assert "id" in data

    def test_list_recipes(self, client, admin_headers):
        r = client.get("/api/recipes/findAll", headers=admin_headers)
        assert r.status_code == 200
        assert isinstance(r.json()["data"], list)
        assert len(r.json()["data"]) >= 1
