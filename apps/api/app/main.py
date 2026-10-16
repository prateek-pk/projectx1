from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from uuid import UUID, uuid7
from datetime import datetime
from app.core.auth import get_current_user, get_authenticated_db
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.models import User

app = FastAPI()

class UserProvisionRequest(BaseModel):
    name: str

class UserResponse(BaseModel):
    id: UUID
    auth_user_id: UUID
    name: str
    created_at: datetime
    updated_at: datetime

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/users/me", response_model=UserResponse)
def provision_user(user_data: UserProvisionRequest, current_user: dict = Depends(get_current_user), db: Session = Depends(get_authenticated_db)):
    auth_user_id = UUID(current_user["sub"])
    user = db.query(User).filter(User.auth_user_id == auth_user_id).first()
    if user is None:
        user = User(
            auth_user_id=auth_user_id,
            name=user_data.name,
        )
        db.add(user)
        db.flush()
        db.refresh(user)
    return user

class WorkspaceCreateRequest(BaseModel):
    name: str
    slug: str
    type: str | None = None

class WorkspaceResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    type: str | None = None
    created_at: datetime
    updated_at: datetime


@app.post("/workspaces", response_model=WorkspaceResponse)
def create_workspace(
    workspace_data: WorkspaceCreateRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_authenticated_db),
):
    auth_user_id = UUID(current_user["sub"])

    user = (
        db.query(User)
        .filter(User.auth_user_id == auth_user_id)
        .first()
    )

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="Swaalay user not found",
        )

    result = db.execute(
        text("""
            SELECT *
            FROM public.create_workspace(
                :workspace_id,
                :membership_id,
                :name,
                :slug,
                :type
            )
        """),
        {
            "workspace_id": uuid7(),
            "membership_id": uuid7(),
            "name": workspace_data.name,
            "slug": workspace_data.slug,
            "type": workspace_data.type,
        },
    ).mappings().one()

    return dict(result)
