"""add pathologies tables

Revision ID: c1d2e3f4a5b6
Revises: bc1de2ef3fa4, l1m2n3o4p5q6
Branch labels: None
Depends on: None
Create Date: 2026-07-02
"""
from alembic import op
import sqlalchemy as sa

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
    from sqlalchemy import inspect, text
    existing = inspect(bind).get_table_names()

    # Add notes column to diets if missing
    cols = [c['name'] for c in inspect(bind).get_columns('diets')]
    if 'notes' not in cols:
        op.add_column('diets', sa.Column('notes', sa.Text(), nullable=True))

    if 'pathologies' not in existing:
        op.create_table(
            'pathologies',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('name', sa.String(255), nullable=False),
            sa.Column('state', sa.Integer(), nullable=False, server_default='1'),
        )
        for name in PATHOLOGIES:
            bind.execute(text("INSERT INTO pathologies (name) VALUES (:n)"), {'n': name})

    if 'diet_pathologies' not in existing:
        op.create_table(
            'diet_pathologies',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('diet_id', sa.String(36), sa.ForeignKey('diets.id', ondelete='CASCADE'), nullable=False),
            sa.Column('pathology_id', sa.Integer(), sa.ForeignKey('pathologies.id', ondelete='CASCADE'), nullable=False),
        )


def downgrade():
    op.drop_table('diet_pathologies')
    op.drop_table('pathologies')
