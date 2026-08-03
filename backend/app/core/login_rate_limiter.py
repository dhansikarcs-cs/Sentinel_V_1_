import logging
import time
from collections import defaultdict

logger = logging.getLogger("sentinel.login_rate_limiter")


class LoginRateLimiter:
    def __init__(self, max_attempts: int = 5, window_seconds: int = 60, lockout_seconds: int = 300):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.lockout_seconds = lockout_seconds
        self._attempts: dict[str, list[float]] = defaultdict(list)
        self._lockouts: dict[str, float] = {}

    def is_locked(self, username: str) -> tuple[bool, int]:
        lockout_end = self._lockouts.get(username, 0)
        now = time.time()
        if now < lockout_end:
            remaining = int(lockout_end - now)
            return True, remaining
        if lockout_end > 0:
            del self._lockouts[username]
            self._attempts.pop(username, None)
        return False, 0

    def record_attempt(self, username: str, success: bool) -> dict:
        now = time.time()
        if success:
            self._attempts.pop(username, None)
            self._lockouts.pop(username, None)
            return {"locked": False, "attempts_remaining": self.max_attempts}

        window_start = now - self.window_seconds
        self._attempts[username] = [t for t in self._attempts[username] if t > window_start]
        self._attempts[username].append(now)

        attempts = len(self._attempts[username])
        remaining = max(0, self.max_attempts - attempts)

        if attempts >= self.max_attempts:
            self._lockouts[username] = now + self.lockout_seconds
            logger.warning(f"Account locked: {username} after {attempts} failed attempts")
            return {"locked": True, "lockout_seconds": self.lockout_seconds, "attempts_remaining": 0}

        return {"locked": False, "attempts_remaining": remaining}


login_rate_limiter = LoginRateLimiter()
