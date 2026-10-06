"""add workspace memberships

Revision ID: 0cc2bc7353b1
Revises: 34c232ba0244
Create Date: 2026-10-05 16:10:48.655423

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0cc2bc7353b1'
down_revision: Union[str, Sequence[str], None] = '34c232ba0244'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('memberships',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('workspace_id', sa.Uuid(), nullable=False),
    sa.Column('role', sa.String(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'workspace_id', name='uq_membership_user_workspace')
    )

    op.execute("""
        CREATE OR REPLACE FUNCTION set_membership_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        CREATE TRIGGER membership_updated_at_trigger
        BEFORE UPDATE ON memberships
        FOR EACH ROW
        EXECUTE FUNCTION set_membership_updated_at();
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP TRIGGER IF EXISTS membership_updated_at_trigger ON memberships;")
    op.execute("DROP FUNCTION IF EXISTS set_membership_updated_at();")
    op.drop_table('memberships')
