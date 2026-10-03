"""establish workspace foundation

Revision ID: 0315aa578a33
Revises: ff6926dc7c60
Create Date: 2026-10-03 13:49:23.634249

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0315aa578a33'
down_revision: Union[str, Sequence[str], None] = 'ff6926dc7c60'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    op.rename_table("businesses", "workspaces")
    op.add_column("workspaces", sa.Column("slug", sa.String(), nullable=True))
    op.add_column("workspaces", sa.Column("type", sa.String(), nullable=True))

    op.execute("""
        UPDATE workspaces
        SET slug = 'workspace-' || id::text
        WHERE slug IS NULL
        """)

    op.alter_column("workspaces", "slug", nullable=False)

    op.create_unique_constraint("uq_workspace_slug", "workspaces", ["slug"])

    op.execute("""
        ALTER TRIGGER business_updated_at_trigger
        ON workspaces
        RENAME TO workspace_updated_at_trigger
        """)

    op.execute("""
        ALTER FUNCTION set_business_updated_at()
        RENAME TO set_workspace_updated_at
        """)

def downgrade() -> None:
    """Downgrade schema."""

    op.execute("""
        ALTER FUNCTION set_workspace_updated_at()
        RENAME TO set_business_updated_at
        """)

    op.execute("""
        ALTER TRIGGER workspace_updated_at_trigger
        ON workspaces
        RENAME TO business_updated_at_trigger
        """)

    op.drop_constraint("uq_workspace_slug", "workspaces", type_="unique")
    op.drop_column("workspaces", "slug")
    op.drop_column("workspaces", "type")
    op.rename_table("workspaces", "businesses")
