"""add row level security policies

Revision ID: 5c9f9bef8416
Revises: e75057e8f8d8
Create Date: 2026-10-15 12:10:45.871568

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5c9f9bef8416'
down_revision: Union[str, Sequence[str], None] = 'e75057e8f8d8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE users ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE users FORCE ROW LEVEL SECURITY")

    op.execute("""
        CREATE POLICY users_select_own
        ON users
        FOR SELECT
        USING (
            auth_user_id =
            NULLIF(current_setting('app.auth_user_id', true), '')::uuid
        )
    """)

    op.execute("""
        CREATE POLICY users_insert_own
        ON users
        FOR INSERT
        WITH CHECK (
            auth_user_id =
            NULLIF(current_setting('app.auth_user_id', true), '')::uuid
        )
    """)

    op.execute("""
        CREATE POLICY users_update_own
        ON users
        FOR UPDATE
        USING (
            auth_user_id =
            NULLIF(current_setting('app.auth_user_id', true), '')::uuid
        )
        WITH CHECK (
            auth_user_id =
            NULLIF(current_setting('app.auth_user_id', true), '')::uuid
        )
    """)


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS users_update_own ON users")
    op.execute("DROP POLICY IF EXISTS users_insert_own ON users")
    op.execute("DROP POLICY IF EXISTS users_select_own ON users")

    op.execute("ALTER TABLE users NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE users DISABLE ROW LEVEL SECURITY")
