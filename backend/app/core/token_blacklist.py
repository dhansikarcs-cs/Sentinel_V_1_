import time

from sqlalchemy import text

from app.core.database import Base, engine
from app.models.revoked_token import RevokedToken


class TokenBlacklist:
    """Persisted (DB-backed) blacklist for revoked JWTs.

    Shared across every worker/process using the same DATABASE_URL, so a token
    revoked by one process is rejected by all of them. Expired entries are
    pruned lazily, keeping reads cheap.
    """

    _DEFAULT_TTL_SECONDS = 86400
    _KEEP_ROWS_SECONDS = 7 * 86400

    def __init__(self):
        self._last_prune = 0.0

    def _ensure_table(self) -> None:
        Base.metadata.create_all(bind=engine, tables=[RevokedToken.__table__], checkfirst=True)

    def revoke(self, jti: str, expires_at: float = 0):
        self._ensure_table()
        expiry = expires_at or (time.time() + self._DEFAULT_TTL_SECONDS)
        with engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO token_blacklist (jti, expires_at) VALUES (:j, :e) "
                    "ON CONFLICT (jti) DO UPDATE SET expires_at = :e"
                ),
                {"j": jti, "e": expiry},
            )

    def is_revoked(self, jti: str) -> bool:
        self._ensure_table()
        now = time.time()
        if now - self._last_prune > 60:
            self._cleanup(now)
        with engine.begin() as conn:
            row = conn.execute(
                text("SELECT 1 FROM token_blacklist WHERE jti = :j AND expires_at > :n"),
                {"j": jti, "n": now},
            ).fetchone()
        return row is not None

    def _cleanup(self, now: float) -> None:
        self._last_prune = now
        cutoff = now - self._KEEP_ROWS_SECONDS
        try:
            with engine.begin() as conn:
                conn.execute(
                    text("DELETE FROM token_blacklist WHERE expires_at < :cutoff"),
                    {"cutoff": cutoff},
                )
        except Exception:
            # cleanup is best-effort; reads remain correct
            pass

    @property
    def count(self) -> int:
        self._ensure_table()
        with engine.begin() as conn:
            row = conn.execute(text("SELECT COUNT(*) FROM token_blacklist")).fetchone()
        return int(row[0]) if row else 0


token_blacklist = TokenBlacklist()
