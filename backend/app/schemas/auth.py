from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr

class UserRegister(BaseModel):
    name: str
    email: str
    password: str
    phone: Optional[str] = None
    state: Optional[str] = None

class UserLogin(BaseModel):
    email: str
    password: str
    portal_hint: Optional[str] = None  # "user" | "admin"

class UserOut(BaseModel):
    id: int
    name: str
    email: str
    role: str
    phone: Optional[str] = None
    state: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
