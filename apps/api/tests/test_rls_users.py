
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.database import SessionLocal


def set_identity(db, auth_user_id):
    db.execute(
        text(
            "SELECT set_config('app.auth_user_id', :auth_user_id, true)"
        ),
        {"auth_user_id": str(auth_user_id)},
    )


def insert_user(db, auth_user_id):
    user_id = uuid4()

    db.execute(
        text("""
            INSERT INTO users (id, auth_user_id, name)
            VALUES (:id, :auth_user_id, :name)
        """),
        {
            "id": str(user_id),
            "auth_user_id": str(auth_user_id),
            "name": "RLS Test User",
        },
    )

    return user_id


def test_users_rls_enforces_identity_isolation():
    user_a_auth_id = uuid4()
    user_b_auth_id = uuid4()
    db = SessionLocal()

    try:
        with db.begin():
            # Create user A under identity A.
            set_identity(db, user_a_auth_id)
            user_a_id = insert_user(db, user_a_auth_id)

            # Create user B under identity B.
            set_identity(db, user_b_auth_id)
            user_b_id = insert_user(db, user_b_auth_id)

            # A can read A's own record.
            set_identity(db, user_a_auth_id)

            own_user = db.execute(
                text("""
                    SELECT id FROM users
                    WHERE auth_user_id = :auth_user_id
                """),
                {"auth_user_id": str(user_a_auth_id)},
            ).scalar_one_or_none()

            assert str(own_user) == str(user_a_id)

            # A cannot read B's record.
            other_user = db.execute(
                text("""
                    SELECT id FROM users
                    WHERE auth_user_id = :auth_user_id
                """),
                {"auth_user_id": str(user_b_auth_id)},
            ).scalar_one_or_none()

            assert other_user is None

            # A cannot insert a record claiming B's identity.
            with pytest.raises(SQLAlchemyError):
                with db.begin_nested():
                    insert_user(db, user_b_auth_id)

            # A cannot change A's identity to B's identity.
            with pytest.raises(SQLAlchemyError):
                with db.begin_nested():
                    db.execute(
                        text("""
                            UPDATE users
                            SET auth_user_id = :other_id
                            WHERE id = :user_id
                        """),
                        {
                            "other_id": str(user_b_auth_id),
                            "user_id": str(user_a_id),
                        },
                    )

    finally:
        db.close()
