from fastapi import FastAPI, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.core.database import get_db


app = FastAPI()

class HealthResponse(BaseModel):
    status: str

class UserCreate(BaseModel):
    name: str
    age: int = Field(gt=0, description="Age must be greater than 0")

@app.post("/users")
def create_user(user: UserCreate):
    return user

@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return {"status": "ok"}

@app.get("/db-demo")
def db_demo(db: Session = Depends(get_db)):
    return {"message": "Database Session connection successful!"}