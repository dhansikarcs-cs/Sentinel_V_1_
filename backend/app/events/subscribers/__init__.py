from app.events.subscribers.audit_subscriber import register_audit_subscribers
from app.events.subscribers.event_store_subscriber import register_event_store_subscribers


def register_all_subscribers(event_bus) -> None:
    event_bus.unsubscribe_all()
    register_audit_subscribers(event_bus)
    register_event_store_subscribers(event_bus)
