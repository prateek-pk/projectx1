"""secure workspace and membership access

Revision ID: 09b87e81e6ff
Revises: 5c9f9bef8416
Create Date: 2026-10-15 12:58:22.629781

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '09b87e81e6ff'
down_revision: Union[str, Sequence[str], None] = '5c9f9bef8416'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None




def upgrade() -> None:
    # Create a dedicated role. Fail if it already exists rather than
    # silently adopting a role whose privileges we have not reviewed.
    op.execute("""
        CREATE ROLE swaalay_rls_helper
        NOLOGIN NOINHERIT BYPASSRLS;
    """)

    op.execute("""
        GRANT USAGE, CREATE ON SCHEMA public
        TO swaalay_rls_helper;

        GRANT SELECT ON
            public.users,
            public.workspaces,
            public.memberships
        TO swaalay_rls_helper;

        GRANT INSERT ON
            public.workspaces,
            public.memberships
        TO swaalay_rls_helper;
    """)

    # Map the verified Supabase identity to Swaalay's internal user ID.
    op.execute("""
        CREATE FUNCTION public.current_swaalay_user_id()
        RETURNS uuid
        LANGUAGE sql
        STABLE
        SECURITY DEFINER
        SET search_path = pg_catalog
        AS $function$
            SELECT u.id
            FROM public.users AS u
            WHERE u.auth_user_id =
                NULLIF(
                    current_setting('app.auth_user_id', true), ''
                )::uuid
        $function$;
    """)

    # Return true if the current user belongs to the workspace.
    op.execute("""
        CREATE FUNCTION public.is_workspace_member(p_workspace_id uuid)
        RETURNS boolean
        LANGUAGE sql
        STABLE
        SECURITY DEFINER
        SET search_path = pg_catalog
        AS $function$
            SELECT EXISTS (
                SELECT 1
                FROM public.memberships AS m
                WHERE m.workspace_id = p_workspace_id
                  AND m.user_id = public.current_swaalay_user_id()
            )
        $function$;
    """)

    # Return true only for an owner membership.
    op.execute("""
        CREATE FUNCTION public.is_workspace_owner(p_workspace_id uuid)
        RETURNS boolean
        LANGUAGE sql
        STABLE
        SECURITY DEFINER
        SET search_path = pg_catalog
        AS $function$
            SELECT EXISTS (
                SELECT 1
                FROM public.memberships AS m
                WHERE m.workspace_id = p_workspace_id
                  AND m.user_id = public.current_swaalay_user_id()
                  AND m.role = 'owner'
            )
        $function$;
    """)

    # Create a workspace and its initial owner membership atomically.
    op.execute("""
        CREATE FUNCTION public.create_workspace(
            p_workspace_id uuid,
            p_membership_id uuid,
            p_name text,
            p_slug text,
            p_type text
        )
        RETURNS SETOF public.workspaces
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = pg_catalog
        AS $function$
        DECLARE
            v_user_id uuid;
            v_auth_user_id uuid;
            v_workspace public.workspaces%ROWTYPE;
        BEGIN
            v_auth_user_id :=
                NULLIF(
                    current_setting('app.auth_user_id', true), ''
                )::uuid;

            IF v_auth_user_id IS NULL THEN
                RAISE EXCEPTION 'Authenticated identity is required';
            END IF;

            SELECT u.id
            INTO v_user_id
            FROM public.users AS u
            WHERE u.auth_user_id = v_auth_user_id;

            IF v_user_id IS NULL THEN
                RAISE EXCEPTION 'Swaalay user not found';
            END IF;

            INSERT INTO public.workspaces (id, name, slug, type)
            VALUES (
                p_workspace_id, p_name, p_slug, p_type
            )
            RETURNING * INTO v_workspace;

            INSERT INTO public.memberships (
                id, user_id, workspace_id, role
            )
            VALUES (
                p_membership_id,
                v_user_id,
                v_workspace.id,
                'owner'
            );

            RETURN NEXT v_workspace;
            RETURN;
        END
        $function$;
    """)

    # Transfer function ownership to the dedicated non-login role.
    # It needs CREATE on public for ownership transfer; revoke it afterward.
    op.execute("""
        ALTER FUNCTION public.current_swaalay_user_id()
        OWNER TO swaalay_rls_helper;

        ALTER FUNCTION public.is_workspace_member(uuid)
        OWNER TO swaalay_rls_helper;

        ALTER FUNCTION public.is_workspace_owner(uuid)
        OWNER TO swaalay_rls_helper;

        ALTER FUNCTION public.create_workspace(
            uuid, uuid, text, text, text
        ) OWNER TO swaalay_rls_helper;

        REVOKE CREATE ON SCHEMA public FROM swaalay_rls_helper;
    """)

    # Functions are executable by PUBLIC by default; restrict that access.
    op.execute("""
        REVOKE ALL ON FUNCTION public.current_swaalay_user_id()
        FROM PUBLIC;

        REVOKE ALL ON FUNCTION public.is_workspace_member(uuid)
        FROM PUBLIC;

        REVOKE ALL ON FUNCTION public.is_workspace_owner(uuid)
        FROM PUBLIC;

        REVOKE ALL ON FUNCTION public.create_workspace(
            uuid, uuid, text, text, text
        ) FROM PUBLIC;

        GRANT EXECUTE ON FUNCTION public.current_swaalay_user_id()
        TO swaalay_runtime;

        GRANT EXECUTE ON FUNCTION public.is_workspace_member(uuid)
        TO swaalay_runtime;

        GRANT EXECUTE ON FUNCTION public.is_workspace_owner(uuid)
        TO swaalay_runtime;

        GRANT EXECUTE ON FUNCTION public.create_workspace(
            uuid, uuid, text, text, text
        ) TO swaalay_runtime;
    """)

    # Workspace reads require membership. Updates require ownership.
    # There are deliberately no direct INSERT or DELETE policies.
    op.execute("""
        ALTER TABLE public.workspaces ENABLE ROW LEVEL SECURITY;
        ALTER TABLE public.workspaces FORCE ROW LEVEL SECURITY;

        CREATE POLICY workspaces_select_member
        ON public.workspaces
        FOR SELECT
        USING (public.is_workspace_member(id));

        CREATE POLICY workspaces_update_owner
        ON public.workspaces
        FOR UPDATE
        USING (public.is_workspace_owner(id))
        WITH CHECK (public.is_workspace_owner(id));
    """)

    # Users may read their own membership rows. Workspace owners may
    # read membership rows for their workspaces. Direct writes are denied.
    op.execute("""
        ALTER TABLE public.memberships ENABLE ROW LEVEL SECURITY;
        ALTER TABLE public.memberships FORCE ROW LEVEL SECURITY;

        CREATE POLICY memberships_select_authorized
        ON public.memberships
        FOR SELECT
        USING (
            user_id = public.current_swaalay_user_id()
            OR public.is_workspace_owner(workspace_id)
        );
    """)


def downgrade() -> None:
    op.execute("""
        DROP POLICY IF EXISTS memberships_select_authorized
        ON public.memberships;

        DROP POLICY IF EXISTS workspaces_update_owner
        ON public.workspaces;

        DROP POLICY IF EXISTS workspaces_select_member
        ON public.workspaces;

        ALTER TABLE public.memberships NO FORCE ROW LEVEL SECURITY;
        ALTER TABLE public.memberships DISABLE ROW LEVEL SECURITY;

        ALTER TABLE public.workspaces NO FORCE ROW LEVEL SECURITY;
        ALTER TABLE public.workspaces DISABLE ROW LEVEL SECURITY;
    """)

    op.execute("""
        DROP FUNCTION IF EXISTS public.create_workspace(
            uuid, uuid, text, text, text
        );

        DROP FUNCTION IF EXISTS public.is_workspace_owner(uuid);
        DROP FUNCTION IF EXISTS public.is_workspace_member(uuid);
        DROP FUNCTION IF EXISTS public.current_swaalay_user_id();
    """)

    # Remove only the privileges this migration granted. Do not use
    # DROP OWNED, which can remove unrelated objects and privileges.
    op.execute("""
        REVOKE ALL ON
            public.users,
            public.workspaces,
            public.memberships
        FROM swaalay_rls_helper;

        REVOKE ALL ON SCHEMA public FROM swaalay_rls_helper;

        DROP ROLE swaalay_rls_helper;
    """)
