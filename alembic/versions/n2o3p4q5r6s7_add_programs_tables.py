"""add programs, program_phases and program_clients tables

Revision ID: n2o3p4q5r6s7
Revises: m1n2o3p4q5r6
Create Date: 2026-06-17

"""
from alembic import op
import sqlalchemy as sa

revision = 'n2o3p4q5r6s7'
down_revision = 'm1n2o3p4q5r6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'programs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('category', sa.String(50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(20), server_default='activo', nullable=True),
        sa.Column('checkins_count', sa.Integer(), server_default='0', nullable=True),
        sa.Column('coach_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['coach_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_programs_coach_id', 'programs', ['coach_id'])
    op.create_index('ix_programs_category', 'programs', ['category'])

    op.create_table(
        'program_phases',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('program_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('weeks', sa.Integer(), nullable=False),
        sa.Column('order', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['program_id'], ['programs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_program_phases_program_id', 'program_phases', ['program_id'])

    op.create_table(
        'program_clients',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('program_id', sa.Integer(), nullable=False),
        sa.Column('client_id', sa.Integer(), nullable=False),
        sa.Column('assigned_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['program_id'], ['programs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['client_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('program_id', 'client_id', name='uq_program_client'),
    )
    op.create_index('ix_program_clients_program_id', 'program_clients', ['program_id'])
    op.create_index('ix_program_clients_client_id', 'program_clients', ['client_id'])


def downgrade() -> None:
    op.drop_table('program_clients')
    op.drop_table('program_phases')
    op.drop_table('programs')
