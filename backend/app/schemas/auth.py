from typing import Literal
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    name: str


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_]+$")
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(min_length=1, max_length=100)
    clinic_code: str = Field(default="", max_length=50)
    role: Literal["patient", "psychologist"] = "patient"
    age: int = Field(default=0, ge=0, le=150)
    occupation: str = Field(default="", max_length=100)
    profession_code: str = Field(default="", max_length=50)
    assigned_psych: str = Field(default="", max_length=50)


class UnlockRequest(BaseModel):
    passphrase: str
