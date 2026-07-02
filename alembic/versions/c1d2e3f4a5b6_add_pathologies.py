"""add pathologies tables

Revision ID: c1d2e3f4a5b6
Revises: bc1de2ef3fa4, l1m2n3o4p5q6
Branch labels: None
Depends on: None
Create Date: 2026-07-02
"""
from alembic import op
from sqlalchemy import text

revision = 'c1d2e3f4a5b6'
down_revision = ('bc1de2ef3fa4', 'l1m2n3o4p5q6')
branch_labels = None
depends_on = None

PATHOLOGIES = [
    'Diabetes tipo 2', 'Resistencia a la insulina', 'Hipotiroidismo', 'SOP',
    'Enfermedad celíaca', 'Crohn/Colitis', 'SIBO', 'Reflujo/GERD',
    'Hipertensión', 'Hipercolesterolemia', 'Gota', 'Insuficiencia renal',
    'Hígado graso', 'Anemia ferropénica', 'Osteoporosis',
    'Intolerancia a la lactosa', 'Alergia al gluten', 'Alergia a frutos secos',
]


def upgrade():
    bind = op.get_bind()

    # Add notes column — ignore error if it already exists
    try:
        bind.execute(text("ALTER TABLE diets ADD COLUMN notes TEXT"))
    except Exception:
        pass

    # Pathologies catalog
    bind.execute(text("""
        CREATE TABLE IF NOT EXISTS pathologies (
            id   INT NOT NULL AUTO_INCREMENT,
            name VARCHAR(255) NOT NULL,
            state INT NOT NULL DEFAULT 1,
            PRIMARY KEY (id)
        ) DEFAULT CHARSET=utf8mb4
    """))

    row = bind.execute(text("SELECT COUNT(*) FROM pathologies")).fetchone()
    if row and row[0] == 0:
        for name in PATHOLOGIES:
            bind.execute(text("INSERT INTO pathologies (name) VALUES (:n)"), {"n": name})

    # Join table
    bind.execute(text("""
        CREATE TABLE IF NOT EXISTS diet_pathologies (
            id           INT NOT NULL AUTO_INCREMENT,
            diet_id      VARCHAR(36) NOT NULL,
            pathology_id INT NOT NULL,
            PRIMARY KEY (id),
            CONSTRAINT fk_dp_diet      FOREIGN KEY (diet_id)      REFERENCES diets(id)       ON DELETE CASCADE,
            CONSTRAINT fk_dp_pathology FOREIGN KEY (pathology_id) REFERENCES pathologies(id) ON DELETE CASCADE
        ) DEFAULT CHARSET=utf8mb4
    """))


def downgrade():
    bind = op.get_bind()
    bind.execute(text("DROP TABLE IF EXISTS diet_pathologies"))
    bind.execute(text("DROP TABLE IF EXISTS pathologies"))
    try:
        bind.execute(text("ALTER TABLE diets DROP COLUMN notes"))
    except Exception:
        pass
