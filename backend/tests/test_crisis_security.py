from datetime import UTC, datetime, timedelta

from app.api.crisis import _make_trustee_link, _trustee_hmac_key, _verify_trustee_link
from app.core.config import settings


def _parse(link: str) -> dict[str, str]:
    query = link.split("?", 1)[1]
    return dict(kv.split("=", 1) for kv in query.split("&"))


def test_valid_link_verifies():
    link = _make_trustee_link("patient_a")
    p = _parse(link)
    assert _verify_trustee_link(p["patient"], int(p["exp"]), p["sig"])


def test_link_is_bound_to_patient():
    link = _make_trustee_link("patient_a")
    p = _parse(link)
    assert not _verify_trustee_link("patient_b", int(p["exp"]), p["sig"])


def test_link_is_bound_to_expiry():
    link = _make_trustee_link("patient_a")
    p = _parse(link)
    assert not _verify_trustee_link(p["patient"], int(p["exp"]) + 999999, p["sig"])


def test_expired_link_rejected():
    import hashlib
    import hmac as hmac_mod

    old_exp = int((datetime.now(UTC) - timedelta(seconds=1)).timestamp())
    message = f"patient_a|{old_exp}"
    sig = hmac_mod.new(_trustee_hmac_key(), message.encode("utf-8"), hashlib.sha256).hexdigest()
    assert not _verify_trustee_link("patient_a", old_exp, sig)


def test_tampered_signature_rejected():
    link = _make_trustee_link("patient_a")
    p = _parse(link)
    assert not _verify_trustee_link(p["patient"], int(p["exp"]), p["sig"][:-2] + "00")


def test_cloud_ai_disabled_by_default():
    assert settings.allow_cloud_ai is False
