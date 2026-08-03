from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user
from app.ml.model_registry import registry
from app.models.user import User

router = APIRouter(prefix="/ml", tags=["ml_registry"])


@router.get("/models")
def list_models(user: User = Depends(get_current_user)):
    return registry.list_models()


@router.get("/models/{name}")
def get_model(name: str, user: User = Depends(get_current_user)):
    model = registry.get_active(name)
    if not model:
        return {"error": "Model not found"}
    return model
