"""La propuesta de IA debe cuadrar con los alimentos reales y con el objetivo."""
import app.core.ai_diet as ai_diet


def _aliment(client, h, name, kcal, p, c, f):
    r = client.post("/api/aliments", headers=h, json={
        "name": name, "calories": kcal, "proteins": p, "carbohydrates": c, "fats": f})
    assert r.status_code == 200, r.text
    return r.json()["data"]["id"]


def test_ai_generate_recalculates_and_filters(client, seed, admin_headers, monkeypatch):
    h = admin_headers
    avena = _aliment(client, h, "Avena", 380, 13, 60, 7)
    pollo = _aliment(client, h, "Pollo", 110, 23, 0, 2)

    captured = {}

    monkeypatch.setattr(ai_diet, "ai_enabled", lambda: True)

    def fake_generate(**kw):
        captured.update(kw)
        return {
            "title": "Plan de prueba", "notes": "Bebe agua.",
            "meals": [
                {"name": "Desayuno", "time": "08:00", "foods": [
                    {"aliment_id": avena, "grams": 100},
                    {"aliment_id": "id-inventado", "grams": 50},   # se descarta
                ]},
                {"name": "Comida", "time": "14:00", "foods": [
                    {"aliment_id": pollo, "grams": 200},
                ]},
            ],
        }

    monkeypatch.setattr(ai_diet, "generate_diet", fake_generate)

    r = client.post("/api/diets/ai-generate", headers=h, json={
        "client_id": None, "kcal": 600, "proteins": 60, "carbs": 60, "fats": 12, "meal_count": 2})
    assert r.status_code == 200, r.text
    d = r.json()["data"]

    # El alimento inventado no aparece
    nombres = [f["name"] for m in d["foods"] for f in m["detail"]]
    assert nombres == ["Avena", "Pollo"], nombres

    # Totales recalculados desde la base de datos: 380 + 220 = 600 kcal
    assert d["totals"]["calories"] == 600
    assert d["totals"]["proteins"] == 59.0   # 13 + 46
    assert d["target"]["deviation_pct"] == 0

    # Al modelo se le pasó el catálogo y el objetivo
    assert captured["target"]["kcal"] == 600
    assert len(captured["aliments"]) >= 2


def test_ai_generate_disabled_without_key(client, seed, admin_headers, monkeypatch):
    monkeypatch.setattr(ai_diet, "ai_enabled", lambda: False)
    r = client.post("/api/diets/ai-generate", headers=admin_headers, json={"kcal": 2000})
    assert r.status_code == 503
    assert "ANTHROPIC_API_KEY" in r.json()["message"]
