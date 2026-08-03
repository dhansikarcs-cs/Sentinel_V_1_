import json
import logging
from app.services.event_store_service import event_store

logger = logging.getLogger("sentinel.subscribers.event_store")


def register_event_store_subscribers(event_bus) -> None:
    def _persist_event(event_type: str = "", **kwargs):
        payload = {k: v for k, v in kwargs.items() if k != "event_type"}
        aggregate_id = kwargs.get("patient_username", kwargs.get("username", ""))
        event_store.append(
            event_type=event_type,
            payload=payload,
            aggregate_type=event_type.split(":")[0] if ":" in event_type else "",
            aggregate_id=str(aggregate_id),
        )

    for event_type in [
        "journal:submitted", "journal:summarized", "journal:viewed",
        "crisis:triggered", "crisis:resolved",
        "mood:logged",
        "booking:created", "booking:status_changed",
        "followup:created",
    ]:
        event_bus.subscribe(event_type, lambda et=event_type, **kw: _persist_event(et, **kw))

    logger.info("Event store subscribers registered")
