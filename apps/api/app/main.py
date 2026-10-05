from re import sub

from fastapi import FastAPI, Depends
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from app.core.auth import get_current_user
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.models import User

app = FastAPI()

class UserProvisionRequest(BaseModel):
    name: str

class UserProvisionResponse(BaseModel):
    id: UUID
    auth_user_id: UUID
    name: str
    created_at: datetime
    updated_at: datetime

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/users/me", response_model=UserProvisionResponse)
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