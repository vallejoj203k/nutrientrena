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
        # El modelo responde por número de catálogo, no por id: se traducen
        # aquí igual que lo hará el endpoint.
        pos = {a.id: i for i, a in enumerate(kw["aliments"])}
        return {
            "title": "Plan de prueba", "notes": "Bebe agua.",
            "meals": [
                {"name": "Desayuno", "time": "08:00", "foods": [
                    {"n": pos[avena], "grams": 100},
                    {"n": 9999, "grams": 50},        # fuera de rango: se descarta
                ]},
                {"name": "Comida", "time": "14:00", "foods": [
                    {"n": pos[pollo], "grams": 200},
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


def test_el_catalogo_se_recorta_equilibrado():
    """El recorte no puede dejar al modelo sin una categoría entera."""
    from app.routers.nutrition.diets import _pick_catalog

    class A:
        def __init__(s, i, n, kcal, p, c, f):
            s.id, s.name, s.brand, s.meal_moments = i, n, None, None
            s.calories, s.proteins, s.carbohydrates, s.fats = kcal, p, c, f

    # Tabla ordenada a propósito: primero 60 proteínas, luego los carbos.
    # Con un `.limit(20)` a secas no entraría ni un carbohidrato.
    catalogo = ([A(f"p{i}", f"Pollo {i}", 110, 23, 0, 2) for i in range(60)]
                + [A(f"c{i}", f"Arroz {i}", 350, 7, 78, 1) for i in range(60)]
                + [A(f"g{i}", f"Aceite {i}", 880, 0, 0, 100) for i in range(20)]
                + [A(f"v{i}", f"Brocoli {i}", 30, 3, 4, 0) for i in range(20)])

    elegidos = _pick_catalog(catalogo, 40)
    assert len(elegidos) == 40
    assert len({a.id for a in elegidos}) == 40          # sin repetidos

    prefijos = {a.id[0] for a in elegidos}
    assert prefijos == {"p", "c", "g", "v"}, prefijos   # las cuatro categorías


def test_si_cabe_entero_no_se_toca():
    from app.routers.nutrition.diets import _pick_catalog

    class A:
        def __init__(s, i):
            s.id, s.name, s.brand, s.meal_moments = i, f"X{i}", None, None
            s.calories, s.proteins, s.carbohydrates, s.fats = 100, 5, 10, 2

    catalogo = [A(str(i)) for i in range(10)]
    assert _pick_catalog(catalogo, 90) is catalogo


def test_clientes_distintos_reciben_alimentos_distintos():
    """Sin esto todas las dietas salían con los mismos alimentos."""
    from app.routers.nutrition.diets import _pick_catalog, _stable_seed

    class A:
        def __init__(s, i, n, kcal, p, c, f):
            s.id, s.name, s.brand, s.meal_moments = i, n, None, None
            s.calories, s.proteins, s.carbohydrates, s.fats = kcal, p, c, f

    catalogo = ([A(f"p{i}", f"Proteína {i}", 110, 23, 0, 2) for i in range(80)]
                + [A(f"c{i}", f"Carbo {i}", 350, 7, 78, 1) for i in range(80)]
                + [A(f"g{i}", f"Grasa {i}", 880, 0, 0, 100) for i in range(30)]
                + [A(f"v{i}", f"Verdura {i}", 30, 3, 4, 0) for i in range(30)])

    def sel(cid, seed=0):
        return {a.id for a in _pick_catalog(catalogo, 90, seed=_stable_seed(cid, seed))}

    a, b = sel("cliente-A"), sel("cliente-B")
    assert a != b, "dos clientes no deberían recibir el mismo subconjunto"
    assert len(a & b) < 80, "se parecen demasiado"

    # Reproducible: el mismo cliente y la misma variante dan lo mismo
    assert sel("cliente-A") == a

    # "Otra variante" cambia el subconjunto
    assert sel("cliente-A", 1) != a

    # Y sigue habiendo de las cuatro categorías
    assert {i[0] for i in a} == {"p", "c", "g", "v"}


def test_la_semilla_es_estable_entre_reinicios():
    """hash() lleva sal por proceso; esto tiene que sobrevivir a un reinicio."""
    from app.routers.nutrition.diets import _stable_seed

    assert _stable_seed("cliente-A", 0) == _stable_seed("cliente-A", 0)
    assert _stable_seed("cliente-A", 0) != _stable_seed("cliente-B", 0)
    assert _stable_seed("cliente-A", 0) != _stable_seed("cliente-A", 1)
    # Valor fijo: si cambia, las dietas ya guardadas dejan de ser reproducibles
    assert _stable_seed("cliente-A", 0) == 488253979


def test_429_de_groq_se_explica(monkeypatch):
    monkeypatch.setattr(ai_diet.settings, "AI_DIET_PROVIDER", "groq")
    monkeypatch.setattr(ai_diet.settings, "GROQ_API_KEY", "gsk-test")

    class _R429:
        status_code = 429
        text = '{"error": {"message": "Rate limit reached..."}}'
        headers = {"retry-after": "42"}

    monkeypatch.setattr(ai_diet.httpx, "post", lambda url, **kw: _R429())
    try:
        ai_diet.generate_diet(client={}, target={"kcal": 2000}, aliments=[])
        assert False, "debería haber lanzado"
    except RuntimeError as e:
        assert "límite" in str(e) and "42 s" in str(e)
        assert "org_" not in str(e)      # sin volcar el error crudo


def test_el_prompt_lleva_los_momentos():
    """Sin esto el modelo no sabía qué alimento es de desayuno."""
    from app.core.ai_diet import build_prompt

    class A:
        def __init__(s, n, mm):
            s.id, s.name, s.brand, s.meal_moments = "x", n, None, mm
            s.calories, s.proteins, s.carbohydrates, s.fats = 100, 5, 10, 2

    msg = build_prompt(client={}, target={"kcal": 1800, "meal_count": 4}, aliments=[
        A("Ternera", "principal"),
        A("Pan integral", "desayuno"),
        A("Huevo", "desayuno,snack,principal"),
    ])
    assert "Ternera [comida/cena]" in msg
    assert "Pan integral [desayuno]" in msg
    # Cuando vale para todo se abrevia en vez de enumerar los tres
    assert "Huevo [cualquiera]" in msg
    # Y la regla que le dice que los respete
    from app.core.ai_diet import SYSTEM_PROMPT
    assert "RESPÉTALOS" in SYSTEM_PROMPT


def test_el_nombre_de_plato_no_cambia_el_alimento(client, seed, admin_headers, monkeypatch):
    """`label` es solo la etiqueta que lee el cliente; el alimento es el real."""
    h = admin_headers
    merluza = _aliment(client, h, "Merluza", 90, 17, 0, 2)

    monkeypatch.setattr(ai_diet, "ai_enabled", lambda: True)
    monkeypatch.setattr(ai_diet, "generate_diet", lambda **kw: {
        "title": "Plan", "notes": "n",
        "meals": [{"name": "Cena", "time": "21:00", "foods": [
            {"n": {a.id: i for i, a in enumerate(kw["aliments"])}[merluza],
             "grams": 200, "label": "Merluza al horno"},
        ]}],
    })

    r = client.post("/api/diets/ai-generate", headers=h, json={
        "client_id": None, "kcal": 600, "meal_count": 2})
    assert r.status_code == 200, r.text
    f = r.json()["data"]["foods"][0]["detail"][0]

    assert f["name"] == "Merluza al horno"     # lo que lee el cliente
    assert f["aliment_id"] == merluza          # el alimento real del catálogo
    assert f["calories"] == 180                # macros de la base de datos: 90 * 2


def test_una_etiqueta_absurda_no_se_cuela(client, seed, admin_headers, monkeypatch):
    h = admin_headers
    merluza = _aliment(client, h, "Merluza", 90, 17, 0, 2)

    monkeypatch.setattr(ai_diet, "ai_enabled", lambda: True)

    def fake(**kw):
        # El índice se busca; dar por hecho el 0 hacía que el test dependiera
        # de qué alimentos hubieran creado los demás.
        i = {a.id: n for n, a in enumerate(kw["aliments"])}[merluza]
        return {"title": "Plan", "notes": "n",
                "meals": [{"name": "Cena", "time": "21:00", "foods": [
                    {"n": i, "grams": 200, "label": "X" * 500},   # etiqueta desmedida
                    {"n": i, "grams": 100, "label": "   "},        # etiqueta vacía
                ]}]}

    monkeypatch.setattr(ai_diet, "generate_diet", fake)

    r = client.post("/api/diets/ai-generate", headers=h, json={"kcal": 600, "meal_count": 2})
    nombres = [f["name"] for f in r.json()["data"]["foods"][0]["detail"]]
    assert nombres == ["Merluza", "Merluza"]   # cae al nombre del catálogo
