import base64
from datetime import timedelta
from sqlalchemy.orm import Session
from ..config import settings
from .. import models
from .crypto import generate_sm4_key, rsa_encrypt_sm4_key, now_utc


def issue_token(db: Session, appkey: str) -> str:
    sm4_key = generate_sm4_key()
    token = rsa_encrypt_sm4_key(sm4_key)
    expires_at = now_utc() + timedelta(seconds=settings.token_ttl_seconds)
    record = models.TokenRecord(
        token=token,
        appkey=appkey,
        sm4_key_b64=base64.b64encode(sm4_key).decode("utf-8"),
        expires_at=expires_at,
    )
    db.add(record)
    db.commit()
    return token


def get_sm4_key(db: Session, token: str) -> bytes | None:
    record = db.query(models.TokenRecord).filter_by(token=token).first()
    if not record:
        return None
    if record.expires_at < now_utc():
        return None
    return base64.b64decode(record.sm4_key_b64)
