import logging
from collections import defaultdict
from collections.abc import Callable
from typing import Any

logger = logging.getLogger("sentinel.events")


class EventBus:
    def __init__(self):
        self._subscribers: dict[str, list[Callable]] = defaultdict(list)

    def subscribe(self, event_type: str, handler: Callable) -> None:
        self._subscribers[event_type].append(handler)
        logger.debug("Subscribed %s to %s", handler.__name__, event_type)

    def unsubscribe(self, event_type: str, handler: Callable) -> None:
        self._subscribers[event_type] = [h for h in self._subscribers[event_type] if h is not handler]

    def emit(self, event_type: str, **data: Any) -> None:
        for handler in self._subscribers.get(event_type, []):
            try:
                handler(**data)
            except Exception as e:
                logger.exception("Event handler %s failed for %s: %s", handler.__name__, event_type, e)


_event_bus = EventBus()


def get_event_bus() -> EventBus:
    return _event_bus
