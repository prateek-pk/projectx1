"""secure capability access

Revision ID: f37d1b9bc5e1
Revises: 09b87e81e6ff
Create Date: 2026-10-16 00:26:39.993172

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'f37d1b9bc5e1'
down_revision: Union[str, Sequence[str], None] = '09b87e81e6ff'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



def upgrade() -> None:
    # The platform capability catalog is readable but not writable
    # by the application runtime role.
    op.execute("""
        REVOKE INSERT, UPDATE, DELETE
        ON public.capabilities
        FROM swaalay_runtime;

        GRANT SELECT
        ON public.capabilities
        TO swaalay_runtime;

        ALTER TABLE public.capabilities
        ENABLE ROW LEVEL SECURITY;

        ALTER TABLE public.capabilities
        FORCE ROW LEVEL SECURITY;

        CREATE POLICY capabilities_select_catalog
        ON public.capabilities
        FOR SELECT
        USING (true);
    """)

    # Workspace-specific capabilities are visible to workspace members.
    op.execute("""
        ALTER TABLE public.workspace_capabilities
        ENABLE ROW LEVEL SECURITY;

        ALTER TABLE public.workspace_capabilities
        FORCE ROW LEVEL SECURITY;

        CREATE POLICY workspace_capabilities_select_member
        ON public.workspace_capabilities
        FOR SELECT
        USING (
            public.is_workspace_member(workspace_id)
        );
    """)

    # Only workspace owners may enable, configure, or remove capabilities.
    op.execute("""
        CREATE POLICY workspace_capabilities_insert_owner
        ON public.workspace_capabilities
        FOR INSERT
        WITH CHECK (
            public.is_workspace_owner(workspace_id)
        );

        CREATE POLICY workspace_capabilities_update_owner
        ON public.workspace_capabilities
        FOR UPDATE
        USING (
            public.is_workspace_owner(workspace_id)
        )
        WITH CHECK (
            public.is_workspace_owner(workspace_id)
        );

        CREATE POLICY workspace_capabilities_delete_owner
        ON public.workspace_capabilities
        FOR DELETE
        USING (
            public.is_workspace_owner(workspace_id)
        );
    """)


def downgrade() -> None:
    op.execute("""
        DROP POLICY IF EXISTS workspace_capabilities_delete_owner
        ON public.workspace_capabilities;

        DROP POLICY IF EXISTS workspace_capabilities_update_owner
        ON public.workspace_capabilities;

        DROP POLICY IF EXISTS workspace_capabilities_insert_owner
        ON public.workspace_capabilities;

        DROP POLICY IF EXISTS workspace_capabilities_select_member
        ON public.workspace_capabilities;

        ALTER TABLE public.workspace_capabilities
        NO FORCE ROW LEVEL SECURITY;

        ALTER TABLE public.workspace_capabilities
        DISABLE ROW LEVEL SECURITY;

        DROP POLICY IF EXISTS capabilities_select_catalog
        ON public.capabilities;

        ALTER TABLE public.capabilities
        NO FORCE ROW LEVEL SECURITY;

        ALTER TABLE public.capabilities
        DISABLE ROW LEVEL SECURITY;

        GRANT SELECT, INSERT, UPDATE, DELETE
        ON public.capabilities
        TO swaalay_runtime;
    """)
