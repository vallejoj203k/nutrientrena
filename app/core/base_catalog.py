"""Catálogo base de alimentos para el generador de dietas.

El catálogo del USDA sirve para consultar macros, no para construir un plan que
lee una persona: sus nombres son de laboratorio ("Abiyuch, sin procesar",
"Alubias blancas, semillas maduras, crudas") y buena parte son ingredientes
crudos o secos que nadie se come así.

Esto es lo contrario: pocos alimentos, con el nombre que usaría un coach al
escribir una dieta, y con el momento del día ya puesto. Es lo que hace que un
desayuno se parezca a un desayuno.

Valores por 100 g de producto tal como se consume (el arroz y la pasta, ya
cocidos; las legumbres, de bote). Son valores de referencia estándar: el coach
puede corregir cualquiera desde la ficha del alimento.

En los alimentos muy ricos en fibra se usan carbohidratos netos, porque el
generador reparte los gramos a partir de estos macros: si las kcal declaradas
no cuadran con proteínas x4 + carbohidratos x4 + grasas x9, las cantidades que
calcula salen mal. Hay un test que lo comprueba entrada por entrada.

Formato: (nombre, grupo, kcal, proteínas, carbohidratos, grasas, momentos)
"""

D = "desayuno"
S = "snack"
P = "principal"
TODO = "desayuno,snack,principal"
DS = "desayuno,snack"

CATALOGO = [
    # ── Cereales, panes y tubérculos ─────────────────────────────────────────
    ("Pan integral", "Panadería y repostería", 247, 9.0, 41.0, 3.5, DS),
    ("Pan blanco", "Panadería y repostería", 265, 8.5, 49.0, 3.2, DS),
    ("Pan de centeno", "Panadería y repostería", 259, 8.5, 48.0, 3.3, DS),
    ("Biscotes integrales", "Panadería y repostería", 380, 12.0, 68.0, 5.0, DS),
    ("Tortitas de arroz", "Panadería y repostería", 387, 8.0, 81.0, 3.0, DS),
    ("Copos de avena", "Cereales de desayuno", 372, 13.0, 59.0, 7.0, DS),
    ("Muesli sin azúcar", "Cereales de desayuno", 360, 10.0, 60.0, 7.5, DS),
    ("Arroz blanco cocido", "Granos y pastas", 130, 2.7, 28.0, 0.3, P),
    ("Arroz integral cocido", "Granos y pastas", 123, 2.6, 26.0, 1.0, P),
    ("Pasta cocida", "Granos y pastas", 158, 5.8, 31.0, 0.9, P),
    ("Pasta integral cocida", "Granos y pastas", 149, 6.0, 30.0, 1.4, P),
    ("Quinoa cocida", "Granos y pastas", 120, 4.4, 21.0, 1.9, P),
    ("Cuscús cocido", "Granos y pastas", 112, 3.8, 23.0, 0.2, P),
    ("Patata cocida", "Verduras y vegetales", 87, 2.0, 20.0, 0.1, P),
    ("Boniato asado", "Verduras y vegetales", 90, 2.0, 21.0, 0.1, P),

    # ── Lácteos y huevos ─────────────────────────────────────────────────────
    ("Leche entera", "Lácteos y huevos", 61, 3.2, 4.8, 3.3, DS),
    ("Leche semidesnatada", "Lácteos y huevos", 46, 3.2, 4.8, 1.6, DS),
    ("Leche desnatada", "Lácteos y huevos", 34, 3.4, 5.0, 0.2, DS),
    ("Bebida de avena", "Lácteos y huevos", 45, 0.8, 7.0, 1.3, DS),
    ("Yogur natural", "Lácteos y huevos", 61, 3.5, 4.7, 3.3, DS),
    ("Yogur griego 0%", "Lácteos y huevos", 59, 10.0, 3.6, 0.4, DS),
    ("Kéfir natural", "Lácteos y huevos", 55, 3.3, 4.5, 2.5, DS),
    ("Queso fresco batido 0%", "Lácteos y huevos", 47, 8.0, 4.0, 0.2, DS),
    ("Requesón", "Lácteos y huevos", 98, 11.0, 3.4, 4.3, DS),
    ("Queso fresco", "Lácteos y huevos", 174, 12.0, 3.0, 12.0, TODO),
    ("Queso curado", "Lácteos y huevos", 402, 25.0, 1.3, 33.0, TODO),
    ("Huevo entero", "Lácteos y huevos", 155, 13.0, 1.1, 11.0, TODO),
    ("Clara de huevo", "Lácteos y huevos", 52, 11.0, 0.7, 0.2, TODO),

    # ── Carnes ───────────────────────────────────────────────────────────────
    ("Pechuga de pollo", "Aves", 110, 23.0, 0.0, 2.0, P),
    ("Muslo de pollo sin piel", "Aves", 155, 19.0, 0.0, 8.5, P),
    ("Pechuga de pavo", "Aves", 104, 24.0, 0.0, 1.0, P),
    ("Solomillo de cerdo", "Cerdo", 143, 21.0, 0.0, 6.0, P),
    ("Lomo de cerdo", "Cerdo", 165, 22.0, 0.0, 8.0, P),
    ("Ternera magra", "Res y vacuno", 158, 22.0, 0.0, 7.5, P),
    ("Carne picada de ternera 5%", "Res y vacuno", 137, 21.0, 0.0, 5.0, P),
    ("Conejo", "Cordero y caza", 136, 21.0, 0.0, 5.5, P),
    ("Jamón serrano", "Embutidos", 241, 31.0, 0.5, 12.0, TODO),
    ("Jamón cocido", "Embutidos", 108, 18.0, 1.5, 3.5, TODO),
    ("Pavo en lonchas", "Embutidos", 104, 18.0, 1.5, 2.8, TODO),

    # ── Pescados y mariscos ──────────────────────────────────────────────────
    ("Merluza", "Pescados y mariscos", 90, 17.0, 0.0, 2.0, P),
    ("Bacalao fresco", "Pescados y mariscos", 82, 18.0, 0.0, 0.7, P),
    ("Dorada", "Pescados y mariscos", 100, 20.0, 0.0, 2.0, P),
    ("Lubina", "Pescados y mariscos", 97, 19.0, 0.0, 2.0, P),
    ("Salmón", "Pescados y mariscos", 208, 20.0, 0.0, 13.0, P),
    ("Salmón ahumado", "Pescados y mariscos", 117, 18.0, 0.0, 4.3, TODO),
    ("Atún fresco", "Pescados y mariscos", 144, 23.0, 0.0, 5.0, P),
    ("Atún al natural en conserva", "Pescados y mariscos", 108, 24.0, 0.0, 1.0, TODO),
    ("Sardinas", "Pescados y mariscos", 208, 25.0, 0.0, 11.5, P),
    ("Caballa", "Pescados y mariscos", 205, 19.0, 0.0, 14.0, P),
    ("Trucha", "Pescados y mariscos", 148, 21.0, 0.0, 7.0, P),
    ("Gambas", "Pescados y mariscos", 99, 21.0, 0.0, 1.5, P),
    ("Mejillones", "Pescados y mariscos", 86, 12.0, 3.7, 2.2, P),
    ("Calamar", "Pescados y mariscos", 92, 16.0, 3.0, 1.4, P),
    ("Pulpo cocido", "Pescados y mariscos", 82, 15.0, 2.2, 1.0, P),

    # ── Legumbres y proteína vegetal ─────────────────────────────────────────
    ("Lentejas cocidas", "Legumbres", 116, 9.0, 20.0, 0.4, P),
    ("Garbanzos cocidos", "Legumbres", 164, 8.9, 27.0, 2.6, P),
    ("Alubias blancas cocidas", "Legumbres", 139, 9.7, 25.0, 0.5, P),
    ("Guisantes", "Legumbres", 81, 5.4, 14.0, 0.4, P),
    ("Tofu firme", "Legumbres", 144, 15.0, 3.0, 8.0, P),
    ("Tempeh", "Legumbres", 192, 20.0, 7.6, 11.0, P),
    ("Soja texturizada", "Legumbres", 336, 52.0, 30.0, 1.5, P),
    ("Hummus", "Legumbres", 166, 8.0, 14.0, 9.6, S),

    # ── Verduras ─────────────────────────────────────────────────────────────
    ("Brócoli", "Verduras y vegetales", 34, 2.8, 7.0, 0.4, P),
    ("Espinacas", "Verduras y vegetales", 23, 2.9, 3.6, 0.4, P),
    ("Acelgas", "Verduras y vegetales", 19, 1.8, 3.7, 0.2, P),
    ("Judías verdes", "Verduras y vegetales", 31, 1.8, 7.0, 0.1, P),
    ("Calabacín", "Verduras y vegetales", 17, 1.2, 3.1, 0.3, P),
    ("Berenjena", "Verduras y vegetales", 25, 1.0, 6.0, 0.2, P),
    ("Pimiento rojo", "Verduras y vegetales", 31, 1.0, 6.0, 0.3, P),
    ("Tomate", "Verduras y vegetales", 18, 0.9, 3.9, 0.2, TODO),
    ("Tomate natural triturado", "Verduras y vegetales", 24, 1.2, 4.5, 0.2, TODO),
    ("Lechuga", "Verduras y vegetales", 15, 1.4, 2.9, 0.2, P),
    ("Zanahoria", "Verduras y vegetales", 41, 0.9, 10.0, 0.2, P),
    ("Cebolla", "Verduras y vegetales", 40, 1.1, 9.3, 0.1, P),
    ("Champiñones", "Verduras y vegetales", 22, 3.1, 3.3, 0.3, P),
    ("Espárragos", "Verduras y vegetales", 20, 2.2, 3.9, 0.1, P),
    ("Alcachofa", "Verduras y vegetales", 47, 3.3, 11.0, 0.2, P),
    ("Coliflor", "Verduras y vegetales", 25, 1.9, 5.0, 0.3, P),
    ("Calabaza", "Verduras y vegetales", 26, 1.0, 6.5, 0.1, P),
    ("Pepino", "Verduras y vegetales", 15, 0.7, 3.6, 0.1, P),
    ("Puerro", "Verduras y vegetales", 61, 1.5, 14.0, 0.3, P),
    ("Setas", "Verduras y vegetales", 22, 3.1, 3.3, 0.3, P),

    # ── Frutas ───────────────────────────────────────────────────────────────
    ("Manzana", "Frutas", 52, 0.3, 14.0, 0.2, DS),
    ("Plátano", "Frutas", 89, 1.1, 23.0, 0.3, DS),
    ("Naranja", "Frutas", 47, 0.9, 12.0, 0.1, DS),
    ("Mandarina", "Frutas", 53, 0.8, 13.0, 0.3, DS),
    ("Pera", "Frutas", 57, 0.4, 15.0, 0.1, DS),
    ("Fresas", "Frutas", 32, 0.7, 7.7, 0.3, DS),
    ("Arándanos", "Frutas", 57, 0.7, 14.0, 0.3, DS),
    ("Kiwi", "Frutas", 61, 1.1, 15.0, 0.5, DS),
    ("Melocotón", "Frutas", 39, 0.9, 10.0, 0.3, DS),
    ("Uvas", "Frutas", 69, 0.7, 18.0, 0.2, DS),
    ("Sandía", "Frutas", 30, 0.6, 7.6, 0.2, DS),
    ("Melón", "Frutas", 34, 0.8, 8.2, 0.2, DS),
    ("Piña", "Frutas", 50, 0.5, 13.0, 0.1, DS),
    ("Mango", "Frutas", 60, 0.8, 15.0, 0.4, DS),
    ("Cerezas", "Frutas", 63, 1.1, 16.0, 0.2, DS),
    ("Dátiles", "Frutas", 282, 2.5, 75.0, 0.4, DS),
    ("Higos secos", "Frutas", 249, 3.3, 64.0, 0.9, DS),

    # ── Frutos secos, semillas y grasas ──────────────────────────────────────
    ("Almendras", "Frutos secos y semillas", 579, 21.0, 22.0, 50.0, DS),
    ("Nueces", "Frutos secos y semillas", 654, 15.0, 14.0, 65.0, DS),
    ("Avellanas", "Frutos secos y semillas", 628, 15.0, 17.0, 61.0, DS),
    ("Pistachos", "Frutos secos y semillas", 560, 20.0, 28.0, 45.0, DS),
    ("Anacardos", "Frutos secos y semillas", 553, 18.0, 30.0, 44.0, DS),
    ("Cacahuetes", "Frutos secos y semillas", 567, 26.0, 16.0, 49.0, DS),
    ("Crema de cacahuete", "Frutos secos y semillas", 588, 25.0, 20.0, 50.0, DS),
    ("Semillas de chía", "Frutos secos y semillas", 486, 17.0, 42.0, 31.0, DS),
    ("Semillas de lino", "Frutos secos y semillas", 534, 18.0, 29.0, 42.0, DS),
    ("Semillas de girasol", "Frutos secos y semillas", 584, 21.0, 20.0, 51.0, DS),
    ("Aceite de oliva virgen extra", "Aceites y grasas", 884, 0.0, 0.0, 100.0, TODO),
    ("Aguacate", "Aceites y grasas", 160, 2.0, 8.5, 15.0, TODO),
    ("Aceitunas", "Aceites y grasas", 115, 0.8, 6.0, 11.0, S),
    ("Mantequilla", "Aceites y grasas", 717, 0.9, 0.1, 81.0, DS),

    # ── Otros de desayuno y meriendas ────────────────────────────────────────
    ("Miel", "Dulces", 304, 0.3, 82.0, 0.0, DS),
    ("Mermelada sin azúcar añadido", "Dulces", 140, 0.5, 33.0, 0.2, DS),
    ("Cacao puro en polvo", "Dulces", 306, 20.0, 25.0, 14.0, DS),
    ("Chocolate negro 85%", "Dulces", 592, 10.0, 19.0, 51.0, DS),
    ("Café solo", "Bebidas", 2, 0.1, 0.0, 0.0, TODO),
]
