import logging

from app.events import EventBus
from app.services.audit import log_audit

logger = logging.getLogger("sentinel.events.audit")


def on_journal_submitted(**data):
    log_audit(
        action="journal_created",
        user=data.get("patient_username", ""),
        role="patient",
        severity="INFO",
        status="success",
        resource=str(data.get("journal_id", "")),
    )


def register_audit_subscribers(event_bus: EventBus) -> None:
    event_bus.subscribe("journal:submitted", on_journal_submitted)
    logger.info("Audit subscribers registered")
