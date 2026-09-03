"""Lo que hace falta para describir una receta como la describe un nutricionista

La receta guardaba el nombre, los macros y poco más. Faltaba todo lo que
decide si una receta le sirve o no a una persona concreta: qué alérgenos
excluye, a qué estilo alimentario pertenece, para qué patologías vale, y las
notas del nutricionista.

Las listas de opción múltiple se guardan como texto separado por comas, igual
que `meal_type` y `categories`, que ya iban así. Las patologías no: hay un
catálogo con su tabla, y una dieta ya se relaciona con él — la receta se
relaciona igual, para que las dos hablen de las mismas patologías y no de dos
listas parecidas.

Al catálogo se le añade el grupo ("Digestivo", "Metabólico"...) porque una
lista plana de treinta patologías no se lee, y las que faltaban.

Revision ID: d6e7f8a90b12
Revises: c5d6e7f8a901
"""
import sqlalchemy as sa
from alembic import op

revision = "d6e7f8a90b12"
down_revision = "c5d6e7f8a901"
branch_labels = None
depends_on = None


COLUMNAS = {
    # Etiquetas libres de la receta ("Alta proteína", "Meal prep"...).
    "tags": sa.String(500),
    # Notas del nutricionista: variaciones, sustituciones, trucos.
    "notes": sa.Text,
    "difficulty": sa.String(20),
    # Alérgenos que la receta NO lleva.
    "allergen_free": sa.String(500),
    "diet_styles": sa.String(500),
    "glycemic_index": sa.String(20),
    "sodium_level": sa.String(20),
    "fiber": sa.Float,
}

# Grupo de cada patología del catálogo que ya existe. Los nombres no se tocan:
# las dietas ya guardadas apuntan a estas filas.
GRUPOS = {
    "Enfermedad celíaca": "Intolerancias",
    "Intolerancia a la lactosa": "Intolerancias",
    "Alergia al gluten": "Intolerancias",
    "Alergia a frutos secos": "Intolerancias",
    "Crohn/Colitis": "Digestivo",
    "SIBO": "Digestivo",
    "Reflujo/GERD": "Digestivo",
    "Diabetes tipo 2": "Metabólico",
    "Resistencia a la insulina": "Metabólico",
    "Hipotiroidismo": "Metabólico",
    "SOP": "Hormonal",
    "Hipertensión": "Cardiovascular",
    "Hipercolesterolemia": "Cardiovascular",
    "Gota": "Renal",
    "Insuficiencia renal": "Renal",
    "Hígado graso": "Hepático",
    "Anemia ferropénica": "Hematológico",
    "Osteoporosis": "Óseo",
}

# Las que faltaban, en el orden en que se enseñan.
NUEVAS = [
    ("Intolerancia a la fructosa", "Intolerancias"),
    ("Intolerancia a la histamina", "Intolerancias"),
    ("SII / FODMAP", "Digestivo"),
    ("H. pylori", "Digestivo"),
    ("Diabetes tipo 1", "Metabólico"),
    ("Hipertiroidismo", "Metabólico"),
    ("Menopausia", "Hormonal"),
    ("Embarazo", "Hormonal"),
    ("Lactancia", "Hormonal"),
    ("Triglicéridos altos", "Cardiovascular"),
    ("Cálculos renales (oxalato)", "Renal"),
    ("Oncología (soporte)", "Otros"),
    ("TCA (recuperación)", "Otros"),
]


def _columnas(bind, tabla):
    return {c["name"] for c in sa.inspect(bind).get_columns(tabla)}


def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)

    hay = _columnas(bind, "recipes")
    for nombre, tipo in COLUMNAS.items():
        if nombre not in hay:
            op.add_column("recipes", sa.Column(nombre, tipo, nullable=True))

    if "grupo" not in _columnas(bind, "pathologies"):
        op.add_column("pathologies", sa.Column("grupo", sa.String(60), nullable=True))

    for nombre, grupo in GRUPOS.items():
        bind.execute(
            sa.text("UPDATE pathologies SET grupo = :g WHERE name = :n AND grupo IS NULL"),
            {"g": grupo, "n": nombre},
        )
    for nombre, grupo in NUEVAS:
        existe = bind.execute(
            sa.text("SELECT 1 FROM pathologies WHERE name = :n"), {"n": nombre}
        ).first()
        if not existe:
            bind.execute(
                sa.text("INSERT INTO pathologies (name, state, grupo) VALUES (:n, 1, :g)"),
                {"n": nombre, "g": grupo},
            )

    if "recipe_pathologies" not in insp.get_table_names():
        op.create_table(
            "recipe_pathologies",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column("recipe_id", sa.Integer,
                      sa.ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False),
            sa.Column("pathology_id", sa.Integer,
                      sa.ForeignKey("pathologies.id", ondelete="CASCADE"), nullable=False),
        )


def downgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "recipe_pathologies" in insp.get_table_names():
        op.drop_table("recipe_pathologies")
    hay = _columnas(bind, "recipes")
    for nombre in COLUMNAS:
        if nombre in hay:
            op.drop_column("recipes", nombre)
    # `pathologies.grupo` y las patologías nuevas se quedan: puede haber dietas
    # y recetas apuntando a ellas.
