from app.ml.model_registry import REGISTRY_PATH, ModelMetadata, ModelRegistry


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_registry_loads_known_models():
    registry = ModelRegistry(REGISTRY_PATH)
    names = {m["name"] for m in registry.list_models()}
    assert "emotion_classifier" in names
    assert "risk_engine" in names


def test_registry_metadata_shape():
    registry = ModelRegistry(REGISTRY_PATH)
    model = registry.get_active("emotion_classifier")
    assert model is not None
    for field in ("name", "version", "model_type", "path", "metrics", "description"):
        assert field in model
    assert model["version"].count(".") == 2


def test_registry_unknown_model_returns_none():
    registry = ModelRegistry(REGISTRY_PATH)
    assert registry.get_active("does_not_exist") is None


def test_register_and_activate_roundtrip(tmp_path):
    reg_path = tmp_path / "registry.json"
    registry = ModelRegistry(reg_path)
    registry.register(
        "test_model",
        "2.0.0",
        "fake",
        "/tmp/model.pkl",
        metrics={"accuracy": 0.9},
        description="test",
    )
    loaded = ModelRegistry(reg_path)
    model = loaded.get_active("test_model")
    assert model["version"] == "2.0.0"
    assert model["metrics"]["accuracy"] == 0.9


def test_model_metadata_roundtrip():
    md = ModelMetadata("m", "1.2.3", "type", "/path", metrics={"a": 1})
    restored = ModelMetadata.from_dict(md.to_dict())
    assert restored.name == "m"
    assert restored.version == "1.2.3"
    assert restored.metrics == {"a": 1}


def test_ml_api_requires_auth(client):
    resp = client.get("/api/ml/models")
    assert resp.status_code == 401


def test_ml_api_returns_models_for_authenticated_user(client, make_user):
    user = make_user()
    resp = client.get("/api/ml/models", headers=_auth(user["access_token"]))
    assert resp.status_code == 200
    names = {m["name"] for m in resp.json()}
    assert "emotion_classifier" in names
