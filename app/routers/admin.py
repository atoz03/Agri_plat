from datetime import datetime, timedelta
import json
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
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


@router.get("/admin/api/bigscreen/summary")
def bigscreen_summary(
    _headers=Depends(require_valid_app_token),
    db: Session = Depends(get_db),
):
    now = datetime.utcnow()
    since_24h = now - timedelta(hours=24)
    since_1h = now - timedelta(hours=1)

    devices_total = db.query(models.Device).count()
    # 在线判定：now - last_report_at <= transmissionIntercal * 3 且 manageStatus=0
    online = 0
    offline = 0
    for last_report_at, transmission_intercal, manage_status in db.query(
        models.Device.last_report_at,
        models.Device.transmissionIntercal,
        models.Device.manageStatus,
    ).all():
        if manage_status == 1 or not last_report_at:
            offline += 1
            continue
        try:
            window_seconds = int(transmission_intercal) * 3
        except Exception:
            window_seconds = 300
        if (now - last_report_at).total_seconds() <= max(60, window_seconds):
            online += 1
        else:
            offline += 1
    device_data_24h = db.query(models.DeviceData).filter(models.DeviceData.created_at >= since_24h).count()
    device_data_1h = db.query(models.DeviceData).filter(models.DeviceData.created_at >= since_1h).count()
    alarm_24h = db.query(models.AlarmDeal).filter(models.AlarmDeal.created_at >= since_24h).count()

    return {
        "resultCode": "200",
        "msg": "成功",
        "devicesTotal": devices_total,
        "devicesOnline": online,
        "devicesOffline": offline,
        "deviceData24h": device_data_24h,
        "deviceData1h": device_data_1h,
        "alarmDeals24h": alarm_24h,
        "updatedAt": now.isoformat(),
    }


@router.get("/admin/api/bigscreen/trends")
def bigscreen_trends(
    hours: int = Query(default=24, ge=1, le=168),
    _headers=Depends(require_valid_app_token),
    db: Session = Depends(get_db),
):
    """
    返回近 N 小时的按小时统计（用于大屏趋势图）。
    注意：SQLite 的 datetime 分组使用 strftime。
    """
    now = datetime.utcnow()
    since = now - timedelta(hours=hours)
    # SQLite：按 UTC 小时切片
    hour_key = func.strftime("%Y-%m-%d %H:00", models.DeviceData.created_at)
    data_rows = (
        db.query(hour_key.label("hour"), func.count(models.DeviceData.id).label("cnt"))
        .filter(models.DeviceData.created_at >= since)
        .group_by("hour")
        .order_by("hour")
        .all()
    )
    alarm_hour_key = func.strftime("%Y-%m-%d %H:00", models.AlarmDeal.created_at)
    alarm_rows = (
        db.query(alarm_hour_key.label("hour"), func.count(models.AlarmDeal.id).label("cnt"))
        .filter(models.AlarmDeal.created_at >= since)
        .group_by("hour")
        .order_by("hour")
        .all()
    )

    return {
        "resultCode": "200",
        "msg": "成功",
        "since": since.isoformat(),
        "now": now.isoformat(),
        "deviceData": [{"hour": h, "count": c} for h, c in data_rows],
        "alarmDeals": [{"hour": h, "count": c} for h, c in alarm_rows],
    }


@router.get("/admin/api/bigscreen/area-stats")
def bigscreen_area_stats(
    top: int = Query(default=20, ge=1, le=200),
    _headers=Depends(require_valid_app_token),
    db: Session = Depends(get_db),
):
    """
    行政区/农场分布统计：省、市、农场（按设备数降序）。
    """
    province_rows = (
        db.query(models.Device.provinceName, func.count(models.Device.deviceCode))
        .group_by(models.Device.provinceName)
        .order_by(func.count(models.Device.deviceCode).desc())
        .limit(top)
        .all()
    )
    city_rows = (
        db.query(models.Device.cityName, func.count(models.Device.deviceCode))
        .group_by(models.Device.cityName)
        .order_by(func.count(models.Device.deviceCode).desc())
        .limit(top)
        .all()
    )
    farm_rows = (
        db.query(models.Device.farmName, func.count(models.Device.deviceCode))
        .group_by(models.Device.farmName)
        .order_by(func.count(models.Device.deviceCode).desc())
        .limit(top)
        .all()
    )
    return {
        "resultCode": "200",
        "msg": "成功",
        "province": [{"name": n or "未知", "count": c} for n, c in province_rows],
        "city": [{"name": n or "未知", "count": c} for n, c in city_rows],
        "farm": [{"name": n or "未知", "count": c} for n, c in farm_rows],
    }


@router.get("/admin/api/bigscreen/latest-alarms")
def bigscreen_latest_alarms(
    limit: int = Query(default=20, ge=1, le=200),
    _headers=Depends(require_valid_app_token),
    db: Session = Depends(get_db),
):
    records = db.query(models.AlarmDeal).order_by(models.AlarmDeal.created_at.desc()).limit(limit).all()
    items = []
    for r in records:
        items.append(
            {
                "id": r.id,
                "created_at": r.created_at.isoformat(),
                "deviceCode": r.deviceCode,
                "alarmCode": r.alarmCode,
                "alarmName": r.alarmName,
                "alarmStatus": r.alarmStatus,
                "handler": r.handler,
                "dept": r.dept,
                "explanation": r.explanation,
            }
        )
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
