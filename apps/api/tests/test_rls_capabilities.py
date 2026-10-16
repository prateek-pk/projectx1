
from uuid import uuid7

import pytest
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.database import SessionLocal


def test_capability_catalog_is_read_only():
    db = SessionLocal()

    try:
        with db.begin():
            # Reading the platform catalog is permitted.
            db.execute(
                text("SELECT id FROM public.capabilities LIMIT 1")
            ).all()

            # The runtime role cannot write to the global catalog.
            operations = [
                """
                INSERT INTO public.capabilities
                    (id, key, name)
                VALUES (:id, :key, :name)
                """,
                """
                UPDATE public.capabilities
                SET name = 'Unauthorized'
                WHERE false
                """,
                """
                DELETE FROM public.capabilities
                WHERE false
                """,
            ]

            for statement in operations:
                with pytest.raises(SQLAlchemyError):
                    with db.begin_nested():
                        db.execute(
                            text(statement),
                            {
                                "id": str(uuid7()),
                                "key": f"test-{uuid7()}",
                                "name": "Unauthorized",
                            },
                        )
    finally:
        db.close()


def test_workspace_capability_policies_are_enabled():
    db = SessionLocal()

    try:
        result = db.execute(
            text("""
                SELECT
                    c.relname,
                    c.relrowsecurity,
                    c.relforcerowsecurity
                FROM pg_class AS c
                JOIN pg_namespace AS n ON n.oid = c.relnamespace
                WHERE n.nspname = 'public'
                  AND c.relname IN (
                      'capabilities',
                      'workspace_capabilities'
                  )
            """)
        ).mappings().all()

        tables = {row["relname"]: row for row in result}

        assert tables["capabilities"]["relrowsecurity"] is True
        assert tables["capabilities"]["relforcerowsecurity"] is True
        assert tables["workspace_capabilities"]["relrowsecurity"] is True
        assert tables["workspace_capabilities"]["relforcerowsecurity"] is True

        policies = set(
            db.execute(
                text("""
                    SELECT policyname
                    FROM pg_policies
                    WHERE schemaname = 'public'
                      AND tablename = 'workspace_capabilities'
                """)
            ).scalars().all()
        )

        assert "workspace_capabilities_select_member" in policies
        assert "workspace_capabilities_insert_owner" in policies
        assert "workspace_capabilities_update_owner" in policies
        assert "workspace_capabilities_delete_owner" in policies
    finally:
        db.close()


def test_nonmember_cannot_insert_workspace_capability():
    db = SessionLocal()

    try:
        with db.begin():
            owner_auth_id = uuid7()
            other_auth_id = uuid7()

            db.execute(
                text(
                    "SELECT set_config('app.auth_user_id', :identity, true)"
                ),
                {"identity": str(owner_auth_id)},
            )

            db.execute(
                text("""
                    INSERT INTO users (id, auth_user_id, name)
                    VALUES (:id, :auth_id, :name)
                """),
                {
                    "id": str(uuid7()),
                    "auth_id": str(owner_auth_id),
                    "name": "Owner Test User",
                },
            )

            workspace = db.execute(
                text("""
                    SELECT id
                    FROM public.create_workspace(
                        :workspace_id,
                        :membership_id,
                        :name,
                        :slug,
                        NULL
                    )
                """),
                {
                    "workspace_id": str(uuid7()),
                    "membership_id": str(uuid7()),
                    "name": "Capability Test Workspace",
                    "slug": f"test-{uuid7()}",
                },
            ).scalar_one()

            # Switch the database identity before creating the second user.
            db.execute(
                text(
                    "SELECT set_config('app.auth_user_id', :identity, true)"
                ),
                {"identity": str(other_auth_id)},
            )

            db.execute(
                text("""
                    INSERT INTO users (id, auth_user_id, name)
                    VALUES (:id, :auth_id, :name)
                """),
                {
                    "id": str(uuid7()),
                    "auth_id": str(other_auth_id),
                    "name": "Nonmember Test User",
                },
            )

            db.execute(
                text(
                    "SELECT set_config('app.auth_user_id', :identity, true)"
                ),
                {"identity": str(other_auth_id)},
            )

            with pytest.raises(SQLAlchemyError) as error:
                with db.begin_nested():
                    db.execute(
                        text("""
                            INSERT INTO public.workspace_capabilities (
                                id, workspace_id, capability_id
                            )
                            VALUES (:id, :workspace_id, :capability_id)
                        """),
                        {
                            "id": str(uuid7()),
                            "workspace_id": str(workspace),
                            "capability_id": str(uuid7()),
                        },
                    )

            # Expect an authorization failure, not a foreign-key failure.
            assert getattr(error.value.orig, "sqlstate", None) == "42501"
    finally:
        db.close()
