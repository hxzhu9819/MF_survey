from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
from dataclasses import dataclass


LOCAL_PEPPER = "LOCAL_PROTOTYPE_CHANGE_ME"


@dataclass(frozen=True)
class FollowupIdentityInput:
    contact_type: str
    contact_value: str
    consent_to_followup: bool


@dataclass(frozen=True)
class FollowupIdentityMaterial:
    contact_type: str
    contact_hash: str
    public_key: str
    retrieval_key: str
    retrieval_key_hash: str


def build_followup_identity(identity: FollowupIdentityInput) -> FollowupIdentityMaterial | None:
    if not identity.consent_to_followup:
        return None
    normalized = normalize_contact(identity.contact_type, identity.contact_value)
    if not normalized:
        return None

    pepper = get_identity_pepper()
    contact_hash = _hmac_hex(pepper, f"contact:{identity.contact_type}:{normalized}")
    public_key = "MF-PUB-" + _hmac_token(pepper, f"public:{identity.contact_type}:{normalized}", 14)

    # The retrieval key is intentionally not derivable from the public key.
    # The participant should keep it like a password for future follow-up.
    retrieval_key = "MF-RET-" + secrets.token_urlsafe(12).replace("_", "A").replace("-", "B").upper()
    retrieval_key_hash = _hmac_hex(pepper, f"retrieval:{retrieval_key}")

    return FollowupIdentityMaterial(
        contact_type=identity.contact_type,
        contact_hash=contact_hash,
        public_key=public_key,
        retrieval_key=retrieval_key,
        retrieval_key_hash=retrieval_key_hash,
    )


def hash_retrieval_key(retrieval_key: str) -> str:
    return _hmac_hex(get_identity_pepper(), f"retrieval:{retrieval_key.strip()}")


def normalize_contact(contact_type: str, value: str) -> str:
    cleaned = "".join(value.strip().split()).lower()
    if contact_type == "wechat":
        return cleaned.replace("微信号:", "").replace("微信：", "")
    return cleaned


def get_identity_pepper() -> str:
    return os.getenv("MF_REGISTRY_IDENTITY_PEPPER", LOCAL_PEPPER)


def using_local_pepper() -> bool:
    return get_identity_pepper() == LOCAL_PEPPER


def _hmac_hex(pepper: str, message: str) -> str:
    return hmac.new(pepper.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).hexdigest()


def _hmac_token(pepper: str, message: str, length: int) -> str:
    digest = hmac.new(pepper.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).digest()
    token = base64.b32encode(digest).decode("ascii").rstrip("=")
    return token[:length]
