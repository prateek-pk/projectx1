
from uuid import uuid4

from sqlalchemy import text

from app.core.auth import get_authenticated_db
from app.core.database import SessionLocal


def test_authenticated_identity_is_transaction_scoped():
    auth_user_id = str(uuid4())
    db = SessionLocal()
    dependency = get_authenticated_db(
        current_user={"sub": auth_user_id},
        db=db,
    )

    try:
        yielded_db = next(dependency)

        current_id = yielded_db.execute(
            text("SELECT current_setting('app.auth_user_id', true)")
        ).scalar_one()

        assert current_id == auth_user_id

        # Finish the dependency's transaction.
        dependency.close()

        # A new transaction must not inherit the previous identity.
        current_id = db.execute(
            text("SELECT current_setting('app.auth_user_id', true)")
        ).scalar_one()

        assert current_id in (None, "")

    finally:
        dependency.close()
        db.close()
