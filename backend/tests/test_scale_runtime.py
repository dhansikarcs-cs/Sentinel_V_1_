"""Scale-runtime tests: pub/sub fan-out, scheduler leader election, config wiring."""

import asyncio

from app.core.config import settings
from app.core.leader import SchedulerLeader
from app.services import ws_pubsub
from app.services.websocket_manager import ConnectionManager


class _FakeWs:
    """Minimal WebSocket stand-in that records sent frames."""

    def __init__(self):
        self.sent: list[str] = []

    async def send_text(self, text: str):
        self.sent.append(text)

    def __eq__(self, other):
        return self is other

    def __hash__(self):
        return id(self)


def test_pubsub_disabled_on_sqlite(monkeypatch):
    # conftest forces a sqlite DATABASE_URL and WS_PUBSUB is unset -> auto
    assert settings.ws_pubsub in ("auto", "pg", "off")
    assert not ws_pubsub.is_postgres()
    assert not ws_pubsub.pubsub_enabled()


def test_ws_pubsub_off_never_enables(monkeypatch):
    monkeypatch.setattr(settings, "ws_pubsub", "off")
    monkeypatch.setattr(settings, "database_url", "postgresql://x:y@h/db")
    assert not ws_pubsub.pubsub_enabled()


def test_ws_pubsub_force_pg(monkeypatch):
    monkeypatch.setattr(settings, "ws_pubsub", "pg")
    monkeypatch.setattr(settings, "database_url", "sqlite:///./data/x.db")
    assert ws_pubsub.pubsub_enabled()


def test_broadcast_local_delivers_when_pubsub_off(monkeypatch):
    monkeypatch.setattr(ws_pubsub, "pubsub_enabled", lambda: False)
    ws = _FakeWs()
    manager = ConnectionManager()
    manager._psych_clients.add(ws)

    async def run():
        await manager.broadcast_to_psych("crisis_alert", {"patient": "p1"})

    asyncio.run(run())
    assert len(ws.sent) == 1
    assert "crisis_alert" in ws.sent[0]


def test_broadcast_publishes_when_pubsub_on(monkeypatch):
    published = []
    monkeypatch.setattr(ws_pubsub, "pubsub_enabled", lambda: True)
    monkeypatch.setattr(ws_pubsub, "publish", lambda payload: published.append(payload))
    ws = _FakeWs()
    manager = ConnectionManager()
    manager._psych_clients.add(ws)

    async def run():
        await manager.broadcast_to_psych("risk_warning", {"patient": "p2"})

    asyncio.run(run())
    assert len(published) == 1
    assert published[0] == {"to": "psych", "event": "risk_warning", "payload": {"patient": "p2"}}
    assert ws.sent == []  # cross-process fan-out delivers via the listener


def test_pubsub_message_dispatches_to_local_clients():
    ws = _FakeWs()
    manager = ConnectionManager()
    manager._psych_clients.add(ws)

    async def scenario():
        manager._loop = asyncio.get_running_loop()
        manager._dispatch_message({"to": "psych", "event": "crisis_alert", "payload": {"patient": "p3"}})
        for _ in range(50):
            await asyncio.sleep(0.01)
            if ws.sent:
                return len(ws.sent)
        return 0

    assert asyncio.run(scenario()) == 1


class _FakeLeaderBackend:
    def __init__(self):
        self.acquired = False
        self.healthy_now = False
        self.fail_acquire = False

    def try_acquire(self) -> bool:
        if self.fail_acquire:
            return False
        self.acquired = True
        self.healthy_now = True
        return True

    def healthy(self) -> bool:
        return self.healthy_now

    def release(self) -> None:
        self.acquired = False
        self.healthy_now = False


def test_leader_sqlite_backend_always_leader(monkeypatch):
    monkeypatch.setattr(settings, "database_url", "sqlite:///./data/x.db")
    leader = SchedulerLeader()

    async def run():
        return await leader.ensure()

    assert asyncio.run(run()) is True


def test_leader_retries_until_backend_acquires():
    backend = _FakeLeaderBackend()
    backend.fail_acquire = True
    leader = SchedulerLeader(backend=backend)

    async def scenario():
        first = await leader.ensure()  # backend refuses -> False
        backend.fail_acquire = False
        second = await leader.ensure()  # now acquires -> True
        return first, second

    first, second = asyncio.run(scenario())
    assert first is False
    assert second is True


def test_leader_loses_leadership_and_reacquires():
    backend = _FakeLeaderBackend()
    leader = SchedulerLeader(backend=backend)

    async def scenario():
        assert await leader.ensure() is True
        backend.healthy_now = False  # simulate dropped connection
        backend.fail_acquire = True  # and PG is temporarily unreachable
        assert await leader.ensure() is False
        backend.fail_acquire = False
        backend.healthy_now = True
        assert await leader.ensure() is True
        return "ok"

    assert asyncio.run(scenario()) == "ok"


def test_runner_module_imports_workers():
    from app.workers.runner import run

    assert callable(run)
