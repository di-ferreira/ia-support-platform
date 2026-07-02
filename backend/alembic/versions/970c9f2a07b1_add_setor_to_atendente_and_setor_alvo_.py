"""add setor to atendente and setor_alvo to chat

Revision ID: 970c9f2a07b1
Revises: 2bb6284d1850
Create Date: 2026-07-02 13:31:30.457127
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '970c9f2a07b1'
down_revision: Union[str, None] = '2bb6284d1850'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('atendente', sa.Column('setor', sa.String(length=50), nullable=True))
    op.add_column('chat', sa.Column('setor_alvo', sa.String(length=50), nullable=True))

def downgrade() -> None:
    op.drop_column('chat', 'setor_alvo')
    op.drop_column('atendente', 'setor')
