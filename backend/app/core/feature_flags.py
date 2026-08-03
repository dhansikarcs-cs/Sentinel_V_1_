import json
import logging
import os
import threading

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

    def set_flag(self, flag_name: str, enabled: bool, rollout_pct: int = 100):
        with self._lock:
            self._flags[flag_name] = {"enabled": enabled, "rollout_pct": rollout_pct}
            self._save()

    def list_flags(self) -> dict:
        with self._lock:
            return dict(self._flags)


feature_flags = FeatureFlags()
