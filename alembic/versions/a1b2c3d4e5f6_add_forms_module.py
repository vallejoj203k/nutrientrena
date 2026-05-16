"""add forms module

Revision ID: a1b2c3d4e5f6
Revises: bb298e505f5b
Create Date: 2026-05-16

"""
from alembic import op
import sqlalchemy as sa

revision = 'a1b2c3d4e5f6'
down_revision = 'bb298e505f5b'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'form_templates',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('is_default', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    op.create_table(
        'form_template_fields',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('form_template_id', sa.Integer(), sa.ForeignKey('form_templates.id'), nullable=False),
        sa.Column('label', sa.String(255), nullable=False),
        sa.Column('field_type', sa.String(50), nullable=False, server_default='text'),
        sa.Column('field_key', sa.String(100), nullable=False),
        sa.Column('placeholder', sa.String(255), nullable=True),
        sa.Column('options', sa.Text(), nullable=True),
        sa.Column('order', sa.Integer(), default=0),
        sa.Column('required', sa.Boolean(), default=True),
    )

    op.create_table(
        'form_assignments',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('form_template_id', sa.Integer(), sa.ForeignKey('form_templates.id'), nullable=False),
        sa.Column('client_user_detail_id', sa.String(36), sa.ForeignKey('user_details.id'), nullable=False),
        sa.Column('assigned_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('status', sa.String(20), server_default='pending'),
        sa.Column('submitted_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )

    op.create_table(
        'form_responses',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('form_assignment_id', sa.String(36), sa.ForeignKey('form_assignments.id'), nullable=False),
        sa.Column('field_key', sa.String(100), nullable=False),
        sa.Column('value', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )


def downgrade():
    op.drop_table('form_responses')
    op.drop_table('form_assignments')
    op.drop_table('form_template_fields')
    op.drop_table('form_templates')
