from sqlalchemy.orm import Session
from .. import models


def write_audit(db: Session, event_type: str, detail: str, ip: str | None = None) -> None:
    record = models.AuditLog(event_type=event_type, detail=detail, ip=ip)
    db.add(record)
    db.commit()
