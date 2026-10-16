
from uuid import uuid7

import pytest
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.database import SessionLocal


def set_identity(db, auth_user_id):
    db.execute(
        text("SELECT set_config('app.auth_user_id', :identity, true)"),
        {"identity": str(auth_user_id)},
    )


def insert_user(db, auth_user_id):
    user_id = uuid7()

    db.execute(
        text("""
            INSERT INTO users (id, auth_user_id, name)
            VALUES (:id, :auth_id, :name)
        """),
        {
            "id": str(user_id),
            "auth_id": str(auth_user_id),
            "name": "RLS Test User",
        },
    )

    return user_id


def create_workspace(db, name, slug):
    return db.execute(
        text("""
            SELECT id, name, slug
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
            "name": name,
            "slug": slug,
        },
    ).mappings().one()


def test_workspace_creation_and_isolation():
    db = SessionLocal()
    transaction = db.begin()

    try:
        user_a = uuid7()
        user_b = uuid7()

        set_identity(db, user_a)
        insert_user(db, user_a)
        workspace_a = create_workspace(db, "Workspace A", f"test-{uuid7()}")

        set_identity(db, user_b)
        insert_user(db, user_b)
        workspace_b = create_workspace(db, "Workspace B", f"test-{uuid7()}")

        # User A can see their own workspace.
        set_identity(db, user_a)

        visible_a = db.execute(
            text("SELECT id FROM workspaces WHERE id = :id"),
            {"id": workspace_a["id"]},
        ).scalar_one_or_none()

        assert str(visible_a) == str(workspace_a["id"])

        # User A cannot see User B's workspace.
        visible_b = db.execute(
            text("SELECT id FROM workspaces WHERE id = :id"),
            {"id": workspace_b["id"]},
        ).scalar_one_or_none()

        assert visible_b is None

        # User A cannot see User B's membership.
        membership_b = db.execute(
            text("""
                SELECT id FROM memberships
                WHERE workspace_id = :workspace_id
            """),
            {"workspace_id": workspace_b["id"]},
        ).scalar_one_or_none()

        assert membership_b is None

    finally:
        transaction.rollback()
        db.close()


def test_workspace_creation_requires_identity():
    db = SessionLocal()

    try:
        with db.begin():
            with pytest.raises(SQLAlchemyError):
                with db.begin_nested():
                    db.execute(
                        text("""
                            SELECT *
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
                            "name": "Should Fail",
                            "slug": f"test-{uuid7()}",
                        },
                    )
    finally:
        db.close()


def test_direct_workspace_and_membership_inserts_are_rejected():
    db = SessionLocal()

    try:
        with db.begin():
            auth_id = uuid7()
            set_identity(db, auth_id)
            user_id = insert_user(db, auth_id)

            workspace = create_workspace(
                db, "Protected Workspace", f"test-{uuid7()}"
            )

            with pytest.raises(SQLAlchemyError):
                with db.begin_nested():
                    db.execute(
                        text("""
                            INSERT INTO workspaces (id, name, slug)
                            VALUES (:id, :name, :slug)
                        """),
                        {
                            "id": str(uuid7()),
                            "name": "Unauthorized",
                            "slug": f"test-{uuid7()}",
                        },
                    )

            with pytest.raises(SQLAlchemyError):
                with db.begin_nested():
                    db.execute(
                        text("""
                            INSERT INTO memberships
                                (id, user_id, workspace_id, role)
                            VALUES (:id, :user_id, :workspace_id, 'owner')
                        """),
                        {
                            "id": str(uuid7()),
                            "user_id": str(user_id),
                            "workspace_id": str(workspace["id"]),
                        },
                    )
    finally:
        db.close()


def test_only_workspace_owner_can_update_workspace():
    db = SessionLocal()

    try:
        with db.begin():
            owner_auth_id = uuid7()
            other_auth_id = uuid7()

            set_identity(db, owner_auth_id)
            insert_user(db, owner_auth_id)
            workspace = create_workspace(
                db, "Original Name", f"test-{uuid7()}"
            )

            set_identity(db, other_auth_id)
            insert_user(db, other_auth_id)

            # A non-member's update must affect zero rows.
            result = db.execute(
                text("""
                    UPDATE workspaces
                    SET name = 'Unauthorized Change'
                    WHERE id = :id
                """),
                {"id": str(workspace["id"])},
            )
            assert result.rowcount == 0

            # The owner can update their own workspace.
            set_identity(db, owner_auth_id)
            result = db.execute(
                text("""
                    UPDATE workspaces
                    SET name = 'Owner Change'
                    WHERE id = :id
                """),
                {"id": str(workspace["id"])},
            )
            assert result.rowcount == 1
    finally:
        db.close()


def test_runtime_and_helper_roles_have_expected_security_settings():
    db = SessionLocal()

    try:
        result = db.execute(
            text("""
                SELECT rolname, rolsuper, rolbypassrls, rolcanlogin
                FROM pg_roles
                WHERE rolname IN (
                    'swaalay_runtime',
                    'swaalay_rls_helper'
                )
            """)
        ).mappings().all()

        roles = {row["rolname"]: row for row in result}

        runtime = roles["swaalay_runtime"]
        helper = roles["swaalay_rls_helper"]

        assert runtime["rolsuper"] is False
        assert runtime["rolbypassrls"] is False

        assert helper["rolsuper"] is False
        assert helper["rolbypassrls"] is True
        assert helper["rolcanlogin"] is False
    finally:
        db.close()
