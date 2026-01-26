import io
import json
from datetime import datetime
from fastapi import APIRouter, Depends, File, UploadFile, Query
from sqlalchemy.orm import Session
import pandas as pd
import pika
from ..deps import get_db
from ..services.exchange_service import save_file_exchange, save_middle_exchange, save_mq_record
from ..schemas import ExchangePublishPayload, MiddleExchangePayload, ExportRequest
from ..config import settings
from .. import models


router = APIRouter()


@router.post("/exchange/file/receive")
async def file_receive(
    db: Session = Depends(get_db),
    file: UploadFile = File(...),
):
    content = await file.read()
    record = save_file_exchange(db, file.filename, content, source="http")
    return {"resultCode": "200", "msg": "成功", "fileId": record.id}


@router.get("/exchange/file/{file_id}")
def file_download(file_id: int, db: Session = Depends(get_db)):
    record = db.query(models.FileExchangeRecord).filter_by(id=file_id).first()
    if not record:
        return {"resultCode": "404", "msg": "文件不存在"}
    return {"resultCode": "200", "msg": "成功", "path": record.path, "checksum": record.checksum}


@router.post("/exchange/middle/push")
def middle_push(payload: MiddleExchangePayload, db: Session = Depends(get_db)):
    record = save_middle_exchange(db, payload.table_name, payload.payload)
    return {"resultCode": "200", "msg": "成功", "id": record.id}


@router.get("/exchange/middle/pull")
def middle_pull(
    since: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    query = db.query(models.MiddleExchangeRecord)
    if since:
        query = query.filter(models.MiddleExchangeRecord.created_at >= datetime.fromisoformat(since))
    items = [
        {"id": r.id, "table_name": r.table_name, "payload": json.loads(r.payload), "created_at": r.created_at.isoformat()}
        for r in query.order_by(models.MiddleExchangeRecord.created_at.asc()).all()
    ]
    return {"resultCode": "200", "msg": "成功", "items": items}


@router.post("/exchange/mq/publish")
def mq_publish(payload: ExchangePublishPayload, db: Session = Depends(get_db)):
    connection = pika.BlockingConnection(pika.URLParameters(settings.rabbitmq_url))
    channel = connection.channel()
    channel.queue_declare(queue=payload.topic, durable=True)
    channel.basic_publish(exchange="", routing_key=payload.topic, body=json.dumps(payload.payload, ensure_ascii=False).encode("utf-8"))
    connection.close()
    save_mq_record(db, payload.topic, payload.payload)
    return {"resultCode": "200", "msg": "成功"}


@router.get("/exchange/mq/history")
def mq_history(db: Session = Depends(get_db)):
    records = db.query(models.MessageQueueRecord).order_by(models.MessageQueueRecord.published_at.desc()).limit(200).all()
    items = [{"topic": r.topic, "payload": json.loads(r.payload), "published_at": r.published_at.isoformat()} for r in records]
    return {"resultCode": "200", "msg": "成功", "items": items}


@router.post("/exchange/export")
def export_devices(req: ExportRequest, db: Session = Depends(get_db)):
    devices = db.query(models.Device).all()
    rows = [d.__dict__ for d in devices]
    for row in rows:
        row.pop("_sa_instance_state", None)
    df = pd.DataFrame(rows)
    if req.format == "json":
        return {"resultCode": "200", "msg": "成功", "data": rows}
    if req.format == "xml":
        xml = df.to_xml(index=False, root_name="devices", row_name="device")
        return {"resultCode": "200", "msg": "成功", "data": xml}
    output = io.BytesIO()
    df.to_excel(output, index=False)
    return {"resultCode": "200", "msg": "成功", "data": output.getvalue().hex()}


@router.post("/exchange/import")
async def import_devices(
    format: str = Query(default="json", pattern="^(json|xml|xls)$"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    content = await file.read()
    if format == "json":
        rows = json.loads(content.decode("utf-8"))
        df = pd.DataFrame(rows)
    elif format == "xml":
        df = pd.read_xml(io.BytesIO(content))
    else:
        df = pd.read_excel(io.BytesIO(content))
    count = 0
    for _, row in df.iterrows():
        data = row.to_dict()
        device_code = str(data.get("deviceCode", ""))
        if not device_code:
            continue
        existing = db.query(models.Device).filter_by(deviceCode=device_code).first()
        if existing:
            for key, value in data.items():
                if hasattr(existing, key):
                    setattr(existing, key, value)
        else:
            db.add(models.Device(**{k: v for k, v in data.items() if k in models.Device.__table__.columns}))
        count += 1
    db.commit()
    return {"resultCode": "200", "msg": "成功", "count": count}
