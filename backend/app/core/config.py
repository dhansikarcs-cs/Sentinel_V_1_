from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    app_name: str = "Sentinel API"
    debug: bool = False

    database_url: str = "sqlite:///./data/sentinel.db"

    jwt_secret: str = "change-me-in-production-use-a-real-secret"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480

    encryption_passphrase: Optional[str] = None
    encryption_salt: str = ""

    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "sentinel"

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    email_from: str = "sentinel@example.com"

    cors_origins: str = "http://localhost:5173"

    class Config:
        env_file = "../../.env"
        env_file_encoding = "utf-8"


settings = Settings()
