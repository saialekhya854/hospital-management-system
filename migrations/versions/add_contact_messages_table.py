"""add contact_messages table

Revision ID: a1b2c3d4e5f6
Revises: 03a2fe00e772
Create Date: 2026-04-25

"""
from alembic import op
import sqlalchemy as sa

revision = 'a1b2c3d4e5f6'
down_revision = '03a2fe00e772'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'contact_messages',
        sa.Column('msg_id',     sa.Integer(), nullable=False),
        sa.Column('name',       sa.String(100), nullable=False),
        sa.Column('email',      sa.String(120), nullable=False),
        sa.Column('phone',      sa.String(20),  nullable=True),
        sa.Column('subject',    sa.String(150), nullable=True),
        sa.Column('message',    sa.Text(),      nullable=False),
        sa.Column('is_read',    sa.Boolean(),   nullable=True, default=False),
        sa.Column('replied_at', sa.DateTime(),  nullable=True),
        sa.Column('created_at', sa.DateTime(),  nullable=True),
        sa.PrimaryKeyConstraint('msg_id')
    )


def downgrade():
    op.drop_table('contact_messages')
