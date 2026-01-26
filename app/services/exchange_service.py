import hashlib
import json
from pathlib import Path
from sqlalchemy.orm import Session
from .. import models
from ..config import settings


def save_file_exchange(db: Session, filename: str, content: bytes, source: str) -> models.FileExchangeRecord:
    exchange_dir = settings.data_dir / "exchange"
    exchange_dir.mkdir(parents=True, exist_ok=True)
    file_path = exchange_dir / filename
    file_path.write_bytes(content)
    checksum = hashlib.sha256(content).hexdigest()
    record = models.FileExchangeRecord(
        filename=filename,
        checksum=checksum,
        size=len(content),
        source=source,
        path=str(file_path),
    )
    db.add(record)
    db.commit()
    return record


def save_middle_exchange(db: Session, table_name: str, payload: dict) -> models.MiddleExchangeRecord:
    record = models.MiddleExchangeRecord(table_name=table_name, payload=json.dumps(payload, ensure_ascii=False))
    db.add(record)
    db.commit()
    return record


def save_mq_record(db: Session, topic: str, payload: dict) -> models.MessageQueueRecord:
    record = models.MessageQueueRecord(topic=topic, payload=json.dumps(payload, ensure_ascii=False))
    db.add(record)
    db.commit()
    return record
