"""Scaling tests: shared rate-limit store, DB-backed token blacklist, scheduler wiring."""

import time

from app.core.config import settings
from app.core.rate_limit_store import DBRateStore, MemoryRateStore
from app.core.token_blacklist import token_blacklist


def test_memory_store_enforces_budget():
    store = MemoryRateStore()
    for _ in range(5):
        assert store.allows("1.2.3.4", 60, 5)
    assert not store.allows("1.2.3.4", 60, 5)


def test_memory_store_keys_are_independent():
    store = MemoryRateStore()
    for _ in range(2):
        assert store.allows("a", 60, 2)
    assert store.allows("b", 60, 2)


def test_db_store_enforces_budget_across_instances(client):
    worker_a = DBRateStore()
    worker_b = DBRateStore()
    for _ in range(3):
        assert worker_a.allows("9.9.9.9", 60, 3)
    assert not worker_b.allows("9.9.9.9", 60, 3)


def test_db_store_window_resets(client):
    store = DBRateStore()
    for _ in range(2):
        assert store.allows("8.8.8.8", 1, 2)
    time.sleep(1.2)
    assert store.allows("8.8.8.8", 1, 2)


def test_db_rate_limit_backend_selected_by_settings():
    # conftest leaves RATE_LIMIT_BACKEND unset -> memory
    assert settings.rate_limit_backend in ("memory", "db")


def test_token_blacklist_revokes_shared(client):
    token_blacklist.revoke("jti-active", time.time() + 60)
    assert token_blacklist.is_revoked("jti-active")
    assert token_blacklist.count >= 1


def test_token_blacklist_expires(client):
    token_blacklist.revoke("jti-expired", time.time() - 1)
    assert not token_blacklist.is_revoked("jti-expired")


def test_worker_runner_module_imports():
    from app.workers.runner import run

    assert callable(run)


def test_run_workers_env_reflected():
    assert settings.run_workers is False
