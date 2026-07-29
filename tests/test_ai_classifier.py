"""La clasificación por momento del día es lo que evita la ternera al desayuno.

Se prueba sin llamar al modelo: lo que importa aquí es que la respuesta se
aplique bien, que no pise lo que el coach marcó a mano y que un fallo no deje
el catálogo a medias.
"""
import app.core.ai_classifier as ai_classifier
from app.core.diet_builder import moments_for


def _aliment(client, h, name, kcal=100, p=10, c=10, f=2, moments=None):
    r = client.post("/api/aliments", headers=h, json={
        "name": name, "calories": kcal, "proteins": p,
        "carbohydrates": c, "fats": f, "meal_moments": moments})
    assert r.status_code == 200, r.text
    return r.json()["data"]["id"]


def _get(client, h, aliment_id):
    r = client.get(f"/api/aliments/{aliment_id}/edit", headers=h)
    assert r.status_code == 200, r.text
    return r.json()["data"]


def test_classify_rellena_los_alimentos_sin_momentos(client, seed, admin_headers, monkeypatch):
    h = admin_headers
    monkeypatch.setattr(ai_classifier, "classify_enabled", lambda: True)
    gazpacho = _aliment(client, h, "Gazpacho")
    tortitas = _aliment(client, h, "Tortitas de arroz Hacendado")

    def fake(aliments):
        # El modelo responde por índice; se comprueba que se mapea al id correcto
        por_nombre = {"Gazpacho": "principal", "Tortitas de arroz Hacendado": "snack"}
        return {a.id: por_nombre[a.name] for a in aliments if a.name in por_nombre}

    monkeypatch.setattr(ai_classifier, "classify", fake)

    r = client.post("/api/aliments/classify-moments", headers=h, json={})
    assert r.status_code == 200, r.text
    assert r.json()["data"]["classified"] >= 2

    assert _get(client, h, gazpacho)["meal_moments"] == "principal"
    assert _get(client, h, tortitas)["meal_moments"] == "snack"


def test_classify_no_pisa_lo_que_marco_el_coach(client, seed, admin_headers, monkeypatch):
    h = admin_headers
    monkeypatch.setattr(ai_classifier, "classify_enabled", lambda: True)
    # El coach ya dijo que su crema de calabaza es de cena
    crema = _aliment(client, h, "Crema de calabaza", moments="principal")

    llamados = []

    def fake(aliments):
        llamados.extend(a.name for a in aliments)
        return {a.id: "desayuno" for a in aliments}

    monkeypatch.setattr(ai_classifier, "classify", fake)
    client.post("/api/aliments/classify-moments", headers=h, json={})

    assert "Crema de calabaza" not in llamados
    assert _get(client, h, crema)["meal_moments"] == "principal"


def test_classify_force_si_recalcula(client, seed, admin_headers, monkeypatch):
    h = admin_headers
    monkeypatch.setattr(ai_classifier, "classify_enabled", lambda: True)
    crema = _aliment(client, h, "Crema de calabaza", moments="desayuno")
    monkeypatch.setattr(ai_classifier, "classify", lambda al: {a.id: "principal" for a in al})

    r = client.post("/api/aliments/classify-moments", headers=h, json={"force": True})
    assert r.status_code == 200, r.text
    assert _get(client, h, crema)["meal_moments"] == "principal"


def test_un_lote_que_falla_no_tumba_el_resto(client, seed, admin_headers, monkeypatch):
    h = admin_headers
    monkeypatch.setattr(ai_classifier, "classify_enabled", lambda: True)
    for i in range(4):
        _aliment(client, h, f"Alimento {i}")

    def fake(aliments):
        if any(a.name == "Alimento 0" for a in aliments):
            raise RuntimeError("la API falló")
        return {a.id: "principal" for a in aliments}

    monkeypatch.setattr(ai_classifier, "classify", fake)
    r = client.post("/api/aliments/classify-moments", headers=h, json={"chunk": 1})
    assert r.status_code == 200, r.text
    d = r.json()["data"]
    assert d["errors"], "el lote que falla debe reportarse"
    assert d["classified"] >= 3, "los demás lotes se guardan igual"


def test_desactivado_sin_clave(client, seed, admin_headers, monkeypatch):
    monkeypatch.setattr(ai_classifier, "classify_enabled", lambda: False)
    r = client.post("/api/aliments/classify-moments", headers=admin_headers, json={})
    assert "AI_CLASSIFY_ENABLED" in r.json()["message"]


def test_crear_alimento_lo_etiqueta_solo(client, seed, admin_headers, monkeypatch):
    monkeypatch.setattr(ai_classifier, "classify_enabled", lambda: True)
    monkeypatch.setattr(ai_classifier, "classify_one", lambda a: "principal")
    gazpacho = _aliment(client, admin_headers, "Gazpacho")
    assert _get(client, admin_headers, gazpacho)["meal_moments"] == "principal"


def test_si_falla_la_clasificacion_el_alimento_se_guarda_igual(client, seed, admin_headers, monkeypatch):
    monkeypatch.setattr(ai_classifier, "classify_enabled", lambda: True)

    def explota(a):
        raise RuntimeError("sin conexión")

    monkeypatch.setattr(ai_classifier, "classify_one", explota)
    gazpacho = _aliment(client, admin_headers, "Gazpacho")
    assert _get(client, admin_headers, gazpacho)["name"] == "Gazpacho"


def test_la_etiqueta_manda_sobre_la_heuristica():
    """Sin etiqueta el gazpacho vale para todo; con ella, solo para principal."""
    class A:
        def __init__(s, name, mm=None):
            s.name, s.meal_moments = name, mm

    assert set(moments_for(A("Gazpacho"))) == {"desayuno", "snack", "principal"}
    assert set(moments_for(A("Gazpacho", "principal"))) == {"principal"}
    # El fallo que motivó todo esto
    assert set(moments_for(A("Crema de calabaza"))) == {"desayuno", "snack"}
    assert set(moments_for(A("Crema de calabaza", "principal"))) == {"principal"}


def test_classify_descarta_respuestas_invalidas(monkeypatch):
    """Índices fuera de rango o momentos inventados no llegan a la base de datos."""
    class A:
        def __init__(s, id, name):
            s.id, s.name, s.brand = id, name, None
            s.calories = s.proteins = s.carbohydrates = s.fats = 0

    aliments = [A("a1", "Avena"), A("a2", "Ternera")]

    class FakeMsg:
        stop_reason = "end_turn"
        content = [type("B", (), {
            "type": "text",
            "text": '{"alimentos": ['
                    '{"n": 0, "momentos": ["desayuno", "brunch"]},'
                    '{"n": 1, "momentos": []},'
                    '{"n": 9, "momentos": ["principal"]}]}',
        })()]

    class FakeAPI:
        def __init__(s, **kw): pass
        @property
        def messages(s): return s
        def create(s, **kw): return FakeMsg()

    import sys, types
    fake_mod = types.ModuleType("anthropic")
    fake_mod.Anthropic = FakeAPI
    monkeypatch.setitem(sys.modules, "anthropic", fake_mod)
    monkeypatch.setattr(ai_classifier.settings, "ANTHROPIC_API_KEY", "test", raising=False)

    out = ai_classifier.classify(aliments)
    assert out == {"a1": "desayuno"}, out
