from fastapi import APIRouter, Depends
from app.core.dependencies import get_current_user, require_role
from app.models.user import User
from app.core.feature_flags import feature_flags

router = APIRouter(prefix="/feature-flags", tags=["feature_flags"])


@router.get("")
def list_flags(user: User = Depends(require_role("psychologist"))):
    return feature_flags.list_flags()


@router.put("/{flag_name}")
def update_flag(flag_name: str, enabled: bool = True, rollout_pct: int = 100, user: User = Depends(require_role("psychologist"))):
    feature_flags.set_flag(flag_name, enabled, rollout_pct)
    return {"status": "ok", "flag": flag_name, "enabled": enabled, "rollout_pct": rollout_pct}
