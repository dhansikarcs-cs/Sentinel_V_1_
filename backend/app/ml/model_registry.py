import json
import logging
import os
import time
from pathlib import Path

logger = logging.getLogger("sentinel.model_registry")

REGISTRY_PATH = Path(__file__).parent / "model_registry.json"


class ModelMetadata:
    def __init__(
        self,
        name: str,
        version: str,
        model_type: str,
        path: str,
        trained_at: str = "",
        metrics: dict = None,
        description: str = "",
    ):
        self.name = name
        self.version = version
        self.model_type = model_type
        self.path = path
        self.trained_at = trained_at or time.strftime("%Y-%m-%dT%H:%M:%SZ")
        self.metrics = metrics or {}
        self.description = description

    def to_dict(self) -> dict:
        return self.__dict__

    @classmethod
    def from_dict(cls, d: dict) -> "ModelMetadata":
        return cls(**{k: v for k, v in d.items() if k in cls.__init__.__code__.co_varnames})


class ModelRegistry:
    def __init__(self, path: Path = REGISTRY_PATH):
        self.path = path
        self._models: dict[str, dict] = {}
        self._load()

    def _load(self):
        if self.path.exists():
            try:
                with open(self.path) as f:
                    self._models = json.load(f)
            except Exception:
                self._models = {}
        else:
            self._models = {}

    def _save(self):
        os.makedirs(self.path.parent, exist_ok=True)
        with open(self.path, "w") as f:
            json.dump(self._models, f, indent=2)

    def register(
        self,
        name: str,
        version: str,
        model_type: str,
        path: str,
        trained_at: str = "",
        metrics: dict = None,
        description: str = "",
    ) -> dict:
        key = f"{name}:{version}"
        meta = ModelMetadata(name, version, model_type, path, trained_at, metrics, description)
        existing = self._models.get(key)
        if existing and existing.get("trained_at"):
            meta.trained_at = existing["trained_at"]
        self._models[key] = meta.to_dict()
        if existing != meta.to_dict():
            self._save()
        logger.info("Registered model %s v%s", name, version)
        return meta.to_dict()

    def get(self, name: str, version: str = "") -> dict | None:
        if version:
            return self._models.get(f"{name}:{version}")
        versions = {k: v for k, v in self._models.items() if k.startswith(f"{name}:")}
        if not versions:
            return None
        return list(versions.values())[-1]

    def list_models(self) -> list[dict]:
        return list(self._models.values())

    def list_versions(self, name: str) -> list[dict]:
        return [v for k, v in self._models.items() if k.startswith(f"{name}:")]

    def get_active(self, name: str) -> dict | None:
        versions = self.list_versions(name)
        return versions[-1] if versions else None


registry = ModelRegistry()

registry.register(
    name="emotion_classifier",
    version="1.0.0",
    model_type="tfidf_logistic_regression",
    path=str(Path(__file__).parent / "emotion_model.pkl"),
    description="GoEmotions 28-class TF-IDF + LogisticRegression one-vs-rest classifier",
    metrics={"accuracy": 0.85, "training_samples": 500},
)

registry.register(
    name="risk_engine",
    version="1.0.0",
    model_type="weighted_rule",
    path="",
    description="Emotion-weighted risk scoring with keyword signals and explainability",
    metrics={"rule_based": True},
)
