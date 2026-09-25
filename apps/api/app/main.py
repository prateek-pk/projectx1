from fastapi import FastAPI
from pydantic import BaseModel, Field

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