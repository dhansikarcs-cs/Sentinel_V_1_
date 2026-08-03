import logging
from typing import Any, Optional

logger = logging.getLogger("sentinel.di")


class ServiceContainer:
    def __init__(self):
        self._services: dict[str, Any] = {}
        self._factories: dict[str, callable] = {}

    def register_singleton(self, name: str, service: Any):
        self._services[name] = service

    def register_factory(self, name: str, factory: callable):
        self._factories[name] = factory

    def get(self, name: str) -> Any:
        if name in self._services:
            return self._services[name]
        if name in self._factories:
            instance = self._factories[name]()
            self._services[name] = instance
            return instance
        raise KeyError(f"Service not registered: {name}")

    def has(self, name: str) -> bool:
        return name in self._services or name in self._factories


container = ServiceContainer()


def register_default_services():
    from app.ml.emotion_classifier import classifier
    from app.ml.model_registry import registry
    from app.core.cqrs import query_bus, command_bus

    container.register_singleton("emotion_classifier", classifier)
    container.register_singleton("model_registry", registry)
    container.register_singleton("query_bus", query_bus)
    container.register_singleton("command_bus", command_bus)

    logger.info("Default services registered in DI container")


register_default_services()
