import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.core.dates import is_valid_dob
from app.core.location import is_valid_tz


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str = ""
    token_type: str = "bearer"
    role: str
    name: str


class RefreshRequest(BaseModel):
    refresh_token: str


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_]+$")
    password: str = Field(min_length=6, max_length=128)
    name: str = Field(min_length=2, max_length=100)
    clinic_code: str = Field(default="", max_length=50)
    role: Literal["patient", "psychologist"] = "patient"
    dob: str = Field(min_length=10, max_length=10)
    occupation: str = Field(min_length=1, max_length=100)
    professional_code: str = Field(default="", max_length=50)
    assigned_psych: str = Field(default="", max_length=50)
    country: str = Field(default="", max_length=100)
    timezone: str = Field(default="", max_length=100)

    @field_validator("timezone")
    @classmethod
    def timezone_valid(cls, v: str) -> str:
        v = v.strip()
        if v and not is_valid_tz(v):
            raise ValueError("timezone must be a valid IANA timezone")
        return v

    @field_validator("name")
    @classmethod
    def name_must_be_real(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("name must be at least 2 characters")
        if not re.search(r"[A-Za-z]", v):
            raise ValueError("name must contain at least one letter")
        return v

    @field_validator("dob")
    @classmethod
    def dob_valid(cls, v: str) -> str:
        v = v.strip()
        if not is_valid_dob(v):
            raise ValueError("dob must be a valid past date (YYYY-MM-DD)")
        return v

    @field_validator("occupation")
    @classmethod
    def occupation_stripped(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("occupation/specialisation is required")
        return v.strip()


class UnlockRequest(BaseModel):
    passphrase: str


class PreferencesUpdate(BaseModel):
    country: str = Field(max_length=100)
    timezone: str = Field(max_length=100)

    @field_validator("timezone")
    @classmethod
    def timezone_valid(cls, v: str) -> str:
        v = v.strip()
        if not is_valid_tz(v):
            raise ValueError("timezone must be a valid IANA timezone")
        return v

    @field_validator("country")
    @classmethod
    def country_stripped(cls, v: str) -> str:
        return v.strip()
