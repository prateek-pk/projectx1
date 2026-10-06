from re import sub

from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from app.core.auth import get_current_user
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.models import User, Workspace, Membership

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
def provision_user(user_data: UserProvisionRequest, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    auth_user_id = UUID(current_user["sub"])
    user = db.query(User).filter(User.auth_user_id == auth_user_id).first()
    if user is None:
        user = User(
            auth_user_id=auth_user_id,
            name=user_data.name,
        )
        db.add(user)
        db.commit()
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
def create_workspace(workspace_data: WorkspaceCreateRequest, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    auth_user_id = UUID(current_user["sub"])
    user = db.query(User).filter(User.auth_user_id == auth_user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="Swaalay user not found")

    workspace = Workspace(
        name=workspace_data.name,
        slug=workspace_data.slug,
        type=workspace_data.type,
    )
    db.add(workspace)
    db.flush()  # Flush to get the workspace ID before creating membership

    membership = Membership(
        user_id=user.id,
        workspace_id=workspace.id,
        role="owner"
    )
    db.add(membership)
    db.commit()
    db.refresh(workspace)

    return workspace
