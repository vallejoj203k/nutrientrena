"""alta del catálogo base para el generador

Da de alta los alimentos con los que el generador construye las dietas: pocos,
con el nombre que escribiría un coach y con el momento del día ya puesto. Los
7.348 del USDA se quedan como referencia nutricional pero fuera del generador.

Idempotente: solo inserta lo que no exista ya con ese nombre, y no toca ningún
alimento existente salvo para marcar los del catálogo como utilizables.

Revision ID: fc2a3b4c5d6e
Revises: fb1f2a3b4c5d
Create Date: 2026-07-29
"""
import uuid
from datetime import datetime

from alembic import op
import sqlalchemy as sa

revision = 'fc2a3b4c5d6e'
down_revision = 'fb1f2a3b4c5d'
branch_labels = None
depends_on = None

# Marca invisible para poder revertir sin tocar lo que ya existía. Va en
# comments y no en brand: brand se muestra en la ficha y viaja en el prompt.
MARCA = "catalogo-base"


def upgrade():
    from app.core.base_catalog import CATALOGO

    bind = op.get_bind()

    # Los grupos se buscan por nombre; los que no existan se crean, porque el
    # grupo es lo que le dice al generador el momento del día por defecto.
    grupos = {
        nombre: gid for gid, nombre in
        bind.execute(sa.text("SELECT id, name FROM group_foods")).fetchall()
    }

    existentes = {
        n for (n,) in
        bind.execute(sa.text("SELECT name FROM aliments WHERE parent_id IS NULL")).fetchall()
    }

    ahora = datetime.utcnow()
    for nombre, grupo, kcal, prot, carb, grasa, momentos in CATALOGO:
        if grupo not in grupos:
            bind.execute(
                sa.text("INSERT INTO group_foods (name, status, created_at, updated_at) "
                        "VALUES (:n, 1, :t, :t)"),
                {"n": grupo, "t": ahora},
            )
            grupos[grupo] = bind.execute(
                sa.text("SELECT id FROM group_foods WHERE name = :n"), {"n": grupo}
            ).scalar()

        if nombre in existentes:
            # Ya estaba (de una ejecución anterior o dado de alta a mano): se
            # marca como utilizable y se le ponen los momentos si no los tiene.
            bind.execute(
                sa.text("UPDATE aliments SET use_in_generator = 1, "
                        "meal_moments = COALESCE(NULLIF(meal_moments, ''), :m) "
                        "WHERE name = :n AND parent_id IS NULL"),
                {"n": nombre, "m": momentos},
            )
            continue

        bind.execute(
            sa.text("""
                INSERT INTO aliments
                    (id, group_food_id, name, comments, quantity, quantity_unit,
                     proteins, carbohydrates, fats, calories, meal_moments,
                     use_in_generator, created_at, updated_at)
                VALUES
                    (:id, :gid, :name, :marca, 100, 'g',
                     :p, :c, :f, :kcal, :m, 1, :t, :t)
            """),
            {"id": str(uuid.uuid4()), "gid": grupos[grupo], "name": nombre,
             "marca": MARCA, "p": prot, "c": carb, "f": grasa, "kcal": kcal,
             "m": momentos, "t": ahora},
        )


def downgrade():
    # Solo se retiran los que insertó esta migración, reconocibles por la marca.
    # Los que ya existían se dejan como están: pueden estar en uso en dietas.
    op.get_bind().execute(
        sa.text("DELETE FROM aliments WHERE comments = :m"), {"m": MARCA}
    )
