"""backfill quantity_unit and quantity_type_id for aliments

Revision ID: d1e2f3a4b5c6
Revises: c1d2e3f4a5b6
Create Date: 2026-07-02
"""
from alembic import op
from sqlalchemy import text

revision = 'd1e2f3a4b5c6'
down_revision = 'c1d2e3f4a5b6'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()

    # --- Step 1: set 'g' as default for all NULL rows ---
    bind.execute(text(
        "UPDATE aliments SET quantity_unit = 'g' WHERE quantity_unit IS NULL"
    ))
    bind.execute(text(
        "UPDATE client_aliments SET quantity_unit = 'g' WHERE quantity_unit IS NULL"
    ))

    # --- Step 2: beverages → ml ---
    bind.execute(text("""
        UPDATE aliments SET quantity_unit = 'ml'
        WHERE quantity_unit = 'g'
          AND (
            name LIKE 'Bebida%'
            OR name LIKE 'Bebidas%'
            OR name LIKE 'Agua%'
            OR name LIKE 'Zumo%'
            OR name LIKE 'Jugo%'
            OR name LIKE 'Refresco%'
            OR name LIKE 'Cerveza%'
            OR name LIKE 'Vino%'
            OR name LIKE 'Licor%'
            OR name LIKE 'Cava%'
            OR name LIKE 'Sidra%'
            OR name LIKE 'Caldo%'
            OR name LIKE 'Infusi%'
            OR LOWER(name) LIKE 'leche%'
            OR group_food_id IN (
                SELECT id FROM group_foods
                WHERE LOWER(name) LIKE '%bebida%'
                   OR LOWER(name) LIKE '%liquido%'
                   OR LOWER(name) LIKE '%líquido%'
                   OR LOWER(name) LIKE '%zumo%'
                   OR LOWER(name) LIKE '%jugo%'
            )
          )
    """))

    # --- Step 3: unit-counted foods → unidad ---
    bind.execute(text("""
        UPDATE aliments SET quantity_unit = 'unidad'
        WHERE quantity_unit = 'g'
          AND (
            name LIKE 'Huevo%'
            OR group_food_id IN (
                SELECT id FROM group_foods
                WHERE LOWER(name) LIKE '%huevo%'
            )
          )
    """))

    # --- Step 4: sync quantity_type_id using parameter_details lookup ---
    bind.execute(text("""
        UPDATE aliments a
        JOIN (
            SELECT pd.id AS pd_id, pd.description AS unit_desc
            FROM parameter_details pd
            JOIN parameters p ON pd.parameter_id = p.id
            WHERE p.description = 'Cantidad'
        ) AS qty ON LOWER(qty.unit_desc) = CASE
            WHEN a.quantity_unit = 'ml'     THEN 'ml'
            WHEN a.quantity_unit = 'unidad' THEN 'ud'
            WHEN a.quantity_unit = 'oz'     THEN 'oz'
            ELSE 'gr'
        END
        SET a.quantity_type_id = qty.pd_id
        WHERE a.quantity_type_id IS NULL
    """))


def downgrade():
    # Non-destructive: just clear the backfilled values
    bind = op.get_bind()
    bind.execute(text("UPDATE aliments SET quantity_type_id = NULL WHERE quantity_type_id IS NOT NULL"))
    bind.execute(text("UPDATE aliments SET quantity_unit = NULL"))
    bind.execute(text("UPDATE client_aliments SET quantity_unit = NULL"))
