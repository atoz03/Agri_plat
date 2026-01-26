import json
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from .. import models
from ..config import settings
from ..security.crypto import sha256_sign


def validate_timestamp(timestamp_ms: int) -> bool:
    now_ms = int(datetime.now(tz=timezone.utc).timestamp() * 1000)
    diff = abs(now_ms - timestamp_ms)
    return diff <= settings.timestamp_window_seconds * 1000


def validate_signature(bus_id: str, cipher: str, timestamp: int, appsecret: str, sign: str) -> bool:
    expected = sha256_sign(bus_id, cipher, timestamp, appsecret)
    return expected == sign


def ensure_idempotent(db: Session, bus_id: str, appkey: str) -> bool:
    exists = db.query(models.IdempotencyRecord).filter_by(bus_id=bus_id).first()
    if exists:
        return False
    record = models.IdempotencyRecord(bus_id=bus_id, appkey=appkey)
    db.add(record)
    db.commit()
    return True


def parse_where(where_payload) -> list[dict]:
    if isinstance(where_payload, str):
        return json.loads(where_payload)
    if isinstance(where_payload, list):
        return where_payload
    return []
