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


# ── Proveedor y datos que salen del servidor ─────────────────────────────────

def _resp(status, payload):
    class _R:
        status_code = status
        text = str(payload)
        @staticmethod
        def json():
            return payload
    return _R()


def test_groq_genera_el_plan(monkeypatch):
    monkeypatch.setattr(ai_diet.settings, "AI_DIET_PROVIDER", "groq")
    monkeypatch.setattr(ai_diet.settings, "GROQ_API_KEY", "gsk-test")
    enviado = {}

    def fake_post(url, **kw):
        enviado.update(kw["json"])
        enviado["url"] = url
        return _resp(200, {"choices": [{"message": {"content":
            '{"title": "Plan", "notes": "n", "meals": []}'}}]})

    monkeypatch.setattr(ai_diet.httpx, "post", fake_post)
    plan = ai_diet.generate_diet(client={}, target={"kcal": 2000}, aliments=[])

    assert plan["title"] == "Plan"
    assert enviado["url"] == ai_diet.GROQ_URL
    assert enviado["response_format"] == {"type": "json_object"}


def test_groq_json_roto_no_pasa_por_bueno(monkeypatch):
    monkeypatch.setattr(ai_diet.settings, "AI_DIET_PROVIDER", "groq")
    monkeypatch.setattr(ai_diet.settings, "GROQ_API_KEY", "gsk-test")
    monkeypatch.setattr(ai_diet.httpx, "post", lambda url, **kw: _resp(
        200, {"choices": [{"message": {"content": "no soy json"}}]}))

    try:
        ai_diet.generate_diet(client={}, target={"kcal": 2000}, aliments=[])
        assert False, "debería haber lanzado"
    except RuntimeError as e:
        assert "JSON" in str(e)


def test_la_clave_depende_del_proveedor(monkeypatch):
    monkeypatch.setattr(ai_diet.settings, "AI_DIET_ENABLED", True)
    monkeypatch.setattr(ai_diet.settings, "ANTHROPIC_API_KEY", None)
    monkeypatch.setattr(ai_diet.settings, "GROQ_API_KEY", "gsk-test")

    monkeypatch.setattr(ai_diet.settings, "AI_DIET_PROVIDER", "groq")
    assert ai_diet.ai_enabled() is True
    assert ai_diet.key_var_name() == "GROQ_API_KEY"

    monkeypatch.setattr(ai_diet.settings, "AI_DIET_PROVIDER", "anthropic")
    assert ai_diet.ai_enabled() is False


def test_el_prompt_no_lleva_identificadores(client, seed, admin_headers, monkeypatch):
    """Lo que sale del servidor no permite saber de quién es la ficha."""
    from app.routers.nutrition import diets as diets_router

    h = admin_headers
    r = client.post("/api/users", headers=h, json={
        "name": "Lucía", "last_name": "Fernández", "email": "lucia@ejemplo.com",
        "password": "Secreta123", "role_id": 6, "age": 34, "weight": 62, "height": 168,
        "allergies": "frutos secos"})
    assert r.status_code == 200, r.text
    cid = r.json()["data"]["id"]

    from app.database import SessionLocal
    db = SessionLocal()
    try:
        ctx = diets_router._client_context(db, cid)
    finally:
        db.close()

    plano = " ".join(f"{k} {v}" for k, v in ctx.items()).lower()
    assert "lucía" not in plano and "lucia" not in plano
    assert "fernández" not in plano and "ejemplo.com" not in plano
    assert cid.lower() not in plano
    assert "ocupación" not in [k.lower() for k in ctx]   # se quitó: no aporta
    # Lo que sí necesita el modelo para proponer un plan:
    assert ctx["Edad"] == 34 and ctx["Peso (kg)"] == 62
    assert ctx["Alergias"] == "frutos secos"
