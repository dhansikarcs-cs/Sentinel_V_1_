import os
import json
import logging
import threading
from typing import Optional

logger = logging.getLogger("sentinel.feature_flags")


class FeatureFlags:
    def __init__(self):
        self._flags: dict[str, dict] = {}
        self._lock = threading.Lock()
        self._load()

    def _load(self):
        flag_file = os.path.join(os.path.dirname(__file__), "..", "..", "feature_flags.json")
        if os.path.exists(flag_file):
            try:
                with open(flag_file) as f:
                    self._flags = json.load(f)
            except Exception:
                self._flags = {}
        else:
            self._flags = {
                "ai_v2_classifier": {"enabled": False, "rollout_pct": 0},
                "risk_engine_v2": {"enabled": False, "rollout_pct": 0},
                "offline_sync": {"enabled": False, "rollout_pct": 0},
                "search_engine": {"enabled": False, "rollout_pct": 0},
                "event_sourcing": {"enabled": True, "rollout_pct": 100},
                "cqrs": {"enabled": True, "rollout_pct": 100},
                "pagination": {"enabled": True, "rollout_pct": 100},
            }
            self._save()

    def _save(self):
        flag_file = os.path.join(os.path.dirname(__file__), "..", "..", "feature_flags.json")
        try:
            with open(flag_file, "w") as f:
                json.dump(self._flags, f, indent=2)
        except Exception:
            pass

    def is_enabled(self, flag_name: str, user_id: str = "") -> bool:
        with self._lock:
            flag = self._flags.get(flag_name)
            if not flag:
                return False
            if not flag.get("enabled", False):
                return False
            rollout = flag.get("rollout_pct", 100)
            if rollout >= 100:
                return True
            if user_id:
                hash_val = hash(user_id) % 100
                return hash_val < rollout
            return True

    def set_flag(self, flag_name: str, enabled: bool, rollout_pct: int = 100):
        with self._lock:
            self._flags[flag_name] = {"enabled": enabled, "rollout_pct": rollout_pct}
            self._save()

    def list_flags(self) -> dict:
        with self._lock:
            return dict(self._flags)


feature_flags = FeatureFlags()
