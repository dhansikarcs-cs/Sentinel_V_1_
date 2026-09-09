from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Sentinel API"
    debug: bool = False

    database_url: str = "sqlite:///./data/sentinel.db"

    jwt_secret: str = "change-me-in-production-use-a-real-secret"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480

    encryption_passphrase: str | None = None
    encryption_salt: str = ""
    encryption_required: bool = True

    ollama_url: str = "http://host.docker.internal:11434"
    ollama_model: str = "sentinel"

    groq_api_key: str = ""

    allow_cloud_ai: bool = False

    trustee_link_secret: str = ""
    trustee_link_expire_seconds: int = 3600
    sentinel_ack_link: str = "http://localhost:5173/trustee"

    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    email_from: str = "sentinel@example.com"
    crisis_helpline_email: str = ""

    cors_origins: str = "http://localhost:5173"
    cookie_secure: bool = False

    rate_limit_max: int = 300
    rate_limit_window: int = 60
    rate_limit_backend: str = "memory"  # "memory" (single process) | "db" (shared via DATABASE_URL)

    # WebSocket fan-out. "auto" enables PostgreSQL LISTEN/NOTIFY whenever
    # DATABASE_URL is postgres (SQLite stays single-process/local); "pg" forces
    # it; "off" disables cross-process broadcast entirely.
    ws_pubsub: str = "auto"

    # Scheduler leader election (PostgreSQL only). Several scheduler replicas may
    # run; exactly one holds the advisory lock and drives the reminder /
    # celebration loops. The lock is released automatically if that process dies,
    # so a replica takes over (failover-safe). Ignored on SQLite.
    scheduler_lock_key: int = 749493
    scheduler_heartbeat_seconds: int = 10

    # Set RUN_WORKERS=false on any process that should NOT run scheduler loops
    # (e.g. uvicorn --workers 4 API boxes); one dedicated process/service runs them.
    run_workers: bool = True

    # Connection pooling for PostgreSQL/MySQL deployments (ignored for SQLite)
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_timeout: int = 30
    db_pool_recycle: int = 1800
    db_pool_pre_ping: bool = True

    class Config:
        env_file = "../.env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
