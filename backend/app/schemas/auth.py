from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    name: str


class RegisterRequest(BaseModel):
    username: str
    password: str
    name: str
    clinic_code: str
    role: str = "patient"
    age: int = 0
    occupation: str = ""
    profession_code: str = ""
    assigned_psych: str = ""


class UnlockRequest(BaseModel):
    passphrase: str
