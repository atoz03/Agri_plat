from datetime import datetime, timedelta
import json
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from ..deps import get_db, require_valid_app_token
from ..config import settings
from .. import models


router = APIRouter()


@router.get("/admin/api/summary")
def summary(
    _headers=Depends(require_valid_app_token),
    db: Session = Depends(get_db),
):
    return {
        "resultCode": "200",
        "msg": "成功",
        "devices": db.query(models.Device).count(),
        "deviceData": db.query(models.DeviceData).count(),
        "alarmDeals": db.query(models.AlarmDeal).count(),
        "auditLogs": db.query(models.AuditLog).count(),
        "fileExchange": db.query(models.FileExchangeRecord).count(),
        "middleExchange": db.query(models.MiddleExchangeRecord).count(),
        "mqRecords": db.query(models.MessageQueueRecord).count(),
    }


@router.get("/admin/api/devices")
def list_devices(
    q: str | None = Query(default=None, description="设备名称或设备编码关键字"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=200),
    _headers=Depends(require_valid_app_token),
    db: Session = Depends(get_db),
):
    query = db.query(models.Device)
    if q:
        like = f"%{q}%"
        query = query.filter((models.Device.deviceName.like(like)) | (models.Device.deviceCode.like(like)))
    total = query.count()
    items = (
        query.order_by(models.Device.updated_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )
    data = []
    for item in items:
        row = item.__dict__.copy()
        row.pop("_sa_instance_state", None)
        row["updated_at"] = row["updated_at"].isoformat() if row.get("updated_at") else None
        data.append(row)
    return {"resultCode": "200", "msg": "成功", "page": page, "limit": limit, "total": total, "items": data}


@router.get("/admin/api/device-data")
def list_device_data(
    deviceCode: str | None = Query(default=None),
    since: str | None = Query(default=None, description="ISO8601 时间，过滤 created_at >= since"),
    limit: int = Query(default=200, ge=1, le=1000),
    _headers=Depends(require_valid_app_token),
    db: Session = Depends(get_db),
):
    query = db.query(models.DeviceData)
    if deviceCode:
        query = query.filter(models.DeviceData.deviceCode == deviceCode)
    if since:
        query = query.filter(models.DeviceData.created_at >= datetime.fromisoformat(since))
    records = query.order_by(models.DeviceData.created_at.desc()).limit(limit).all()
    items = []
    for r in records:
        try:
            content = json.loads(r.content)
        except Exception:
            content = r.content
        items.append(
            {
                "id": r.id,
                "deviceCode": r.deviceCode,
                "messageType": r.messageType,
                "reportTime": r.reportTime,
                "content": content,
                "created_at": r.created_at.isoformat(),
            }
        )
    return {"resultCode": "200", "msg": "成功", "items": items}


@router.get("/admin/api/alarm-deals")
def list_alarm_deals(
    deviceCode: str | None = Query(default=None),
    since: str | None = Query(default=None, description="ISO8601 时间，过滤 created_at >= since"),
    limit: int = Query(default=200, ge=1, le=1000),
    _headers=Depends(require_valid_app_token),
    db: Session = Depends(get_db),
):
    query = db.query(models.AlarmDeal)
    if deviceCode:
        query = query.filter(models.AlarmDeal.deviceCode == deviceCode)
    if since:
        query = query.filter(models.AlarmDeal.created_at >= datetime.fromisoformat(since))
    records = query.order_by(models.AlarmDeal.created_at.desc()).limit(limit).all()
    items = []
    for r in records:
        try:
            enclosures = json.loads(r.enclosures) if r.enclosures else None
        except Exception:
            enclosures = r.enclosures
        items.append(
            {
                "id": r.id,
                "deviceCode": r.deviceCode,
                "alarmCode": r.alarmCode,
                "alarmName": r.alarmName,
                "alarmStatus": r.alarmStatus,
                "dealTime": r.dealTime,
                "handler": r.handler,
                "dept": r.dept,
                "explanation": r.explanation,
                "enclosures": enclosures,
                "created_at": r.created_at.isoformat(),
            }
        )
    return {"resultCode": "200", "msg": "成功", "items": items}


@router.get("/admin/api/audit-logs")
def list_audit_logs(
    event_type: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
    _headers=Depends(require_valid_app_token),
    db: Session = Depends(get_db),
):
    query = db.query(models.AuditLog)
    if event_type:
        query = query.filter(models.AuditLog.event_type == event_type)
    records = query.order_by(models.AuditLog.created_at.desc()).limit(limit).all()
    items = [
        {"id": r.id, "event_type": r.event_type, "detail": r.detail, "ip": r.ip, "created_at": r.created_at.isoformat()}
        for r in records
    ]
    return {"resultCode": "200", "msg": "成功", "items": items}


@router.post("/admin/retention/cleanup")
def retention_cleanup(
    _headers=Depends(require_valid_app_token),
    db: Session = Depends(get_db),
):
    cutoff = datetime.utcnow() - timedelta(days=settings.retention_days)
    deleted = db.query(models.DeviceData).filter(models.DeviceData.created_at < cutoff).delete()
    db.commit()
    return {"resultCode": "200", "msg": "成功", "deleted": deleted}
