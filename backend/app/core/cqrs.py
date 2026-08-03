import logging
from typing import Any

from app.core.database import SessionLocal

logger = logging.getLogger("sentinel.cqrs")


class QueryBus:
    def __init__(self):
        self._handlers: dict[str, callable] = {}

    def register(self, query_type: str, handler: callable):
        self._handlers[query_type] = handler

    def execute(self, query_type: str, **kwargs) -> Any:
        handler = self._handlers.get(query_type)
        if not handler:
            raise ValueError(f"No handler registered for query: {query_type}")
        return handler(**kwargs)


class CommandBus:
    def __init__(self):
        self._handlers: dict[str, callable] = {}

    def register(self, command_type: str, handler: callable):
        self._handlers[command_type] = handler

    def execute(self, command_type: str, **kwargs) -> Any:
        handler = self._handlers.get(command_type)
        if not handler:
            raise ValueError(f"No handler registered for command: {command_type}")
        return handler(**kwargs)


query_bus = QueryBus()
command_bus = CommandBus()


def register_default_handlers():
    from app.repositories import JournalRepository

    def get_journals(patient_username: str, page: int = 1, page_size: int = 20):
        from app.core.pagination import paginate

        db = SessionLocal()
        try:
            repo = JournalRepository(db)
            items = repo.get_by_patient(patient_username)
            return paginate(items, page=page, page_size=page_size)
        finally:
            db.close()

    def get_risk_history(patient_username: str, limit: int = 50):
        from app.models.risk_assessment import RiskAssessment

        db = SessionLocal()
        try:
            return (
                db.query(RiskAssessment)
                .filter(RiskAssessment.patient_username == patient_username)
                .order_by(RiskAssessment.created_at.desc())
                .limit(limit)
                .all()
            )
        finally:
            db.close()

    query_bus.register("get_journals", get_journals)
    query_bus.register("get_risk_history", get_risk_history)
    logger.info("Default CQRS handlers registered")


register_default_handlers()
