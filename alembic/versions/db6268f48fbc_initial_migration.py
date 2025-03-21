"""Initial migration

Revision ID: db6268f48fbc
Revises: 
Create Date: 2025-03-21 17:23:42.206662

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = 'db6268f48fbc'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    inspector = inspect(conn)
    
    # Check if indexes exist before dropping
    indexes = {index['name'] for index in inspector.get_indexes('expenses')}
    if 'ix_expenses_id' in indexes:
        op.drop_index('ix_expenses_id', table_name='expenses')
    
    tables = inspector.get_table_names()
    if 'expenses' in tables:
        op.drop_table('expenses')
    
    indexes = {index['name'] for index in inspector.get_indexes('users')}
    if 'ix_users_id' in indexes:
        op.drop_index('ix_users_id', table_name='users')
    
    if 'users' in tables:
        op.drop_table('users')

def downgrade() -> None:
    """Downgrade schema."""
    op.create_table('users',
        sa.Column('id', sa.INTEGER(), server_default=sa.text("nextval('users_id_seq'::regclass)"), autoincrement=True, nullable=False),
        sa.Column('first_name', sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column('last_name', sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column('email', sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column('hashed_password', sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.PrimaryKeyConstraint('id', name='users_pkey'),
        sa.UniqueConstraint('email', name='users_email_key'),
        postgresql_ignore_search_path=False
    )
    op.create_index('ix_users_id', 'users', ['id'], unique=False)
    
    op.create_table('expenses',
        sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column('amount', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=False),
        sa.Column('category', sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column('date', sa.DATE(), autoincrement=False, nullable=False),
        sa.Column('description', sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column('user_id', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='expenses_user_id_fkey'),
        sa.PrimaryKeyConstraint('id', name='expenses_pkey')
    )
    op.create_index('ix_expenses_id', 'expenses', ['id'], unique=False)
