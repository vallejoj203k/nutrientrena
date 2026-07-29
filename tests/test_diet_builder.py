"""El generador por algoritmo debe cuadrar con el objetivo y respetar restricciones."""
from app.core import diet_builder


class A:
    """Alimento mínimo, con macros por 100 g."""
    def __init__(self, id, name, kcal, p, c, f, brand=None):
        self.id, self.name = id, name
        self.calories, self.proteins, self.carbohydrates, self.fats = kcal, p, c, f
        self.brand = brand


CATALOGO = [
    A("p1", "Pechuga de pollo", 110, 23, 0, 2),
    A("p2", "Salmón", 208, 20, 0, 13),
    A("p3", "Huevo", 155, 13, 1, 11),
    A("p4", "Yogur griego 0%", 59, 10, 4, 0.4),
    A("c1", "Arroz integral", 355, 7, 74, 3),
    A("c2", "Avena", 380, 13, 60, 7),
    A("c3", "Patata", 77, 2, 17, 0.1),
    A("c4", "Pan integral", 247, 9, 41, 3),
    A("f1", "Aceite de oliva", 884, 0, 0, 100),
    A("f2", "Almendras", 579, 21, 22, 50),
    A("v1", "Brócoli", 34, 3, 7, 0.4),
    A("v2", "Espinacas", 23, 3, 4, 0.4),
]


def _totales(plan):
    return plan["totals"]


def test_clasifica_por_macros():
    c = diet_builder.classify
    assert c(A("x", "Pollo", 110, 23, 0, 2)) == "protein"
    assert c(A("x", "Arroz", 355, 7, 74, 3)) == "carb"
    assert c(A("x", "Aceite", 884, 0, 0, 100)) == "fat"
    assert c(A("x", "Brócoli", 34, 3, 7, 0.4)) == "veg"
    assert c(A("x", "Sin datos", 0, 0, 0, 0)) is None


def test_cuadra_con_el_objetivo():
    plan = diet_builder.build_diet(
        aliments=CATALOGO, kcal=2100, proteins=160, carbs=200, fats=70, meal_count=4)
    kcal = _totales(plan)["calories"]
    desvio = abs(kcal - 2100) / 2100
    assert desvio <= 0.10, f"{kcal} kcal se aleja demasiado de 2100"
    assert len(plan["meals"]) == 4
    # Cantidades redondeadas y utilizables
    for m in plan["meals"]:
        for f in m["detail"]:
            assert f["quantity_calc"] in diet_builder.STEPS, f


def test_respeta_alergias_y_disgustos():
    restr = diet_builder.parse_restrictions("Frutos secos, almendras", "lactosa", "salmón")
    plan = diet_builder.build_diet(
        aliments=CATALOGO, kcal=2000, proteins=150, carbs=200, fats=60,
        meal_count=4, restrictions=restr)
    nombres = [f["name"].lower() for m in plan["meals"] for f in m["detail"]]
    assert not any("almendra" in n for n in nombres), nombres
    assert not any("salmon" in n or "salmón" in n for n in nombres), nombres


def test_es_reproducible_y_la_semilla_cambia_la_variante():
    kw = dict(aliments=CATALOGO, kcal=2000, proteins=150, carbs=200, fats=60, meal_count=4)
    a = diet_builder.build_diet(**kw, seed=1)
    b = diet_builder.build_diet(**kw, seed=1)
    c = diet_builder.build_diet(**kw, seed=7)
    plano = lambda p: [(f["name"], f["quantity_calc"]) for m in p["meals"] for f in m["detail"]]
    assert plano(a) == plano(b), "mismos datos deberían dar el mismo plan"
    assert plano(a) != plano(c), "otra semilla debería dar otra variante"


def test_sin_catalogo_util_avisa():
    try:
        diet_builder.build_diet(aliments=[A("v", "Lechuga", 15, 1, 3, 0.2)],
                                kcal=2000, proteins=150, carbs=200, fats=60)
    except ValueError as e:
        assert "proteína" in str(e)
    else:
        raise AssertionError("debería avisar de que falta catálogo")


def test_endpoint_auto_generate(client, seed, admin_headers):
    h = admin_headers
    for a in CATALOGO:
        client.post("/api/aliments", headers=h, json={
            "name": a.name, "calories": a.calories, "proteins": a.proteins,
            "carbohydrates": a.carbohydrates, "fats": a.fats})
    r = client.post("/api/diets/auto-generate", headers=h, json={
        "kcal": 2100, "proteins": 160, "carbs": 200, "fats": 70, "meal_count": 4})
    assert r.status_code == 200, r.text
    d = r.json()["data"]
    assert abs(d["target"]["deviation_pct"]) <= 10
    assert len(d["foods"]) == 4


def test_ia_desactivada_por_defecto(client, seed, admin_headers):
    r = client.post("/api/diets/ai-generate", headers=admin_headers, json={"kcal": 2000})
    assert r.status_code == 503
    assert "AI_DIET_ENABLED" in r.json()["message"]


def test_patologias_excluyen_familias_de_alimentos():
    """La celiaquía no aparece en el nombre de ningún alimento: hace falta el mapa."""
    fuera = diet_builder.exclusions_for(["Enfermedad celíaca"])
    assert "pan" in fuera and "trigo" in fuera

    restr = diet_builder.parse_restrictions("") + fuera
    plan = diet_builder.build_diet(
        aliments=CATALOGO, kcal=2000, proteins=150, carbs=200, fats=60,
        meal_count=4, restrictions=restr)
    nombres = [f["name"].lower() for m in plan["meals"] for f in m["detail"]]
    assert not any("pan" in n or "avena" in n for n in nombres), nombres
    # Sigue construyendo un plan válido con lo que queda
    assert abs(plan["totals"]["calories"] - 2000) / 2000 <= 0.10


def test_lactosa_respeta_los_productos_sin_lactosa():
    catalogo = CATALOGO + [A("s1", "Yogur sin lactosa", 60, 10, 4, 0.5)]
    restr = diet_builder.exclusions_for(["Intolerancia a la lactosa"])
    assert not diet_builder.is_allowed(A("y", "Yogur griego 0%", 59, 10, 4, 0.4), restr)
    assert diet_builder.is_allowed(catalogo[-1], restr)


def test_patologia_sin_exclusiones_no_filtra_nada():
    """La diabetes se maneja ajustando macros, no quitando alimentos."""
    assert diet_builder.exclusions_for(["Diabetes tipo 2"]) == []


def test_avisos_distinguen_lo_aplicado_de_lo_que_revisa_el_coach():
    avisos = diet_builder.warnings_for(["Enfermedad celíaca", "Diabetes tipo 2"])
    por_nombre = {a["pathology"]: a for a in avisos}

    cel = por_nombre["Enfermedad celíaca"]
    assert cel["applied"] is True
    assert "excluido" in cel["text"]

    dia = por_nombre["Diabetes tipo 2"]
    assert dia["applied"] is False
    assert "carbohidratos" in dia["text"]


def test_patologia_desconocida_avisa_igualmente():
    a = diet_builder.warnings_for(["Condición rara"])[0]
    assert a["applied"] is False and a["text"]


def test_sin_patologias_no_hay_avisos():
    assert diet_builder.warnings_for([]) == []
    assert diet_builder.warnings_for(None) == []


# ── Lógica de comidas: qué encaja en cada momento del día ────────────────────

def _con(n, m=None):
    a = A("x", n, 100, 10, 10, 2)
    a.meal_moments = m
    return a


def test_deduce_el_momento_por_el_nombre():
    assert diet_builder.moments_for(_con("Ternera magra")) == ["principal"]
    assert diet_builder.moments_for(_con("Lentejas")) == ["principal"]
    assert diet_builder.moments_for(_con("Avena")) == ["desayuno", "snack"]
    assert diet_builder.moments_for(_con("Yogur griego")) == ["desayuno", "snack"]
    # Ambiguos: valen para todo
    assert set(diet_builder.moments_for(_con("Huevo"))) == set(diet_builder.MOMENTS)
    # Desconocido: no se descarta
    assert set(diet_builder.moments_for(_con("Alimento raro"))) == set(diet_builder.MOMENTS)


def test_la_etiqueta_del_coach_manda_sobre_la_deduccion():
    assert diet_builder.moments_for(_con("Ternera magra", "desayuno")) == ["desayuno"]
    # Una etiqueta inválida no rompe: se vuelve a la deducción
    assert diet_builder.moments_for(_con("Ternera magra", "cualquiera")) == ["principal"]


def test_no_pone_carne_ni_arroz_en_el_desayuno():
    catalogo = [
        A("p1", "Ternera magra", 150, 26, 0, 5),
        A("p2", "Yogur griego 0%", 59, 10, 4, 0.4),
        A("c1", "Arroz integral", 355, 7, 74, 3),
        A("c2", "Avena", 380, 13, 60, 7),
        A("f1", "Aceite de oliva", 884, 0, 0, 100),
        A("v1", "Brócoli", 34, 3, 7, 0.4),
    ]
    plan = diet_builder.build_diet(aliments=catalogo, kcal=2000, proteins=150,
                                   carbs=200, fats=60, meal_count=4)
    desayuno = next(m for m in plan["meals"] if m["name"] == "Desayuno")
    nombres = [f["name"] for f in desayuno["detail"]]
    assert "Ternera magra" not in nombres, nombres
    assert "Arroz integral" not in nombres, nombres
    # Y la comida sí puede llevarlos
    comida = next(m for m in plan["meals"] if m["name"] == "Comida")
    assert any(n in ["Ternera magra", "Arroz integral"] for n in [f["name"] for f in comida["detail"]])


def test_la_distribucion_desplaza_las_calorias_sin_cambiar_el_total():
    kw = dict(aliments=CATALOGO, kcal=2000, proteins=150, carbs=200, fats=60, meal_count=4)
    eq = diet_builder.build_diet(**kw)
    bb = diet_builder.build_diet(**kw, distribution="big_breakfast")

    kcal_desayuno = lambda p: sum(
        f["calories"] for m in p["meals"] if m["name"] == "Desayuno" for f in m["detail"])
    assert kcal_desayuno(bb) > kcal_desayuno(eq), (kcal_desayuno(bb), kcal_desayuno(eq))
    # El total sigue cuadrando con el objetivo
    assert abs(bb["totals"]["calories"] - 2000) / 2000 <= 0.12


def test_splits_siempre_suman_uno():
    for n in (2, 3, 4, 5, 6):
        for dist in diet_builder.DISTRIBUTIONS:
            assert abs(sum(diet_builder._splits_for(n, dist)) - 1) < 1e-9, (n, dist)


def test_no_cuela_impropios_cuando_el_catalogo_no_da():
    """Antes metía pescado crudo en el desayuno si no había proteína apta."""
    class G:
        def __init__(s, n): s.name = n

    class A:
        def __init__(s, i, n, g, kcal, p, c, f):
            s.id, s.name, s.brand, s.meal_moments = i, n, None, None
            s.group_food = G(g)
            s.calories, s.proteins, s.carbohydrates, s.fats = kcal, p, c, f

    # Catálogo sin ninguna proteína de desayuno
    catalogo = [
        A("1", "Abadejo de Alaska, crudo", "Mariscos, crustáceos y moluscos", 72, 17.3, 0.1, 1.0),
        A("2", "Manzana", "Frutas", 52, 0.3, 14, 0.2),
        A("3", "Aceite de oliva", "Aceites y grasas", 884, 0, 0, 100),
        A("4", "Arroz", "Granos y pastas", 350, 7, 78, 1),
        A("5", "Acelgas", "Verduras y vegetales", 19, 1.8, 3.7, 0.2),
    ]
    plan = diet_builder.build_diet(aliments=catalogo, kcal=1800, proteins=140,
                                   carbs=160, fats=60, meal_count=4, seed=7)

    desayuno = next(m for m in plan["meals"] if m["name"] == "Desayuno")
    nombres = [f["name"] for f in desayuno["detail"]]
    assert "Abadejo de Alaska, crudo" not in nombres, nombres

    # Y se avisa de lo que falta, en vez de rellenar con cualquier cosa
    assert any("Desayuno" in g and "proteínas" in g for g in plan["gaps"]), plan["gaps"]


def test_sin_huecos_no_hay_aviso():
    class G:
        def __init__(s, n): s.name = n

    class A:
        def __init__(s, i, n, g, kcal, p, c, f):
            s.id, s.name, s.brand, s.meal_moments = i, n, None, None
            s.group_food = G(g)
            s.calories, s.proteins, s.carbohydrates, s.fats = kcal, p, c, f

    catalogo = [
        A("1", "Huevo", "Lácteos y huevos", 155, 13, 1, 11),
        A("8", "Yogur griego 0%", "Lácteos y huevos", 59, 10, 4, 0),
        A("2", "Pan integral", "Panadería y repostería", 250, 9, 45, 3),
        A("3", "Pollo", "Aves", 110, 23, 0, 2),
        A("4", "Arroz", "Granos y pastas", 350, 7, 78, 1),
        A("5", "Aceite de oliva", "Aceites y grasas", 884, 0, 0, 100),
        A("6", "Manzana", "Frutas", 52, 0.3, 14, 0.2),
        A("7", "Acelgas", "Verduras y vegetales", 19, 1.8, 3.7, 0.2),
    ]
    plan = diet_builder.build_diet(aliments=catalogo, kcal=1800, proteins=140,
                                   carbs=160, fats=60, meal_count=4, seed=3)
    assert plan["gaps"] == [], plan["gaps"]


def test_el_huevo_cuenta_como_proteina():
    """Por reparto calórico salía 'grasa' y el desayuno se quedaba sin proteína."""
    class A:
        def __init__(s, kcal, p, c, f):
            s.name = "x"
            s.calories, s.proteins, s.carbohydrates, s.fats = kcal, p, c, f

    assert diet_builder.classify(A(155, 13, 1, 11)) == "protein"      # huevo
    assert diet_builder.classify(A(402, 25, 1.3, 33)) == "protein"    # queso curado
    # Pero un fruto seco no es la proteína de una comida por tener 21 g
    assert diet_builder.classify(A(579, 21, 22, 50)) == "fat"         # almendras
    assert diet_builder.classify(A(654, 15, 14, 65)) == "fat"         # nueces
