import json
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from ..schemas import CommonRequest, CommonResponse, DeviceSyncPayload, DeviceDataPayload
from ..deps import get_db, decrypt_common_payload
from .. import models
from ..utils.audit import write_audit
from ..services.data_transform import standardize_device_data


router = APIRouter()


@router.post("/api/device/deviceSync", response_model=CommonResponse)
def device_sync(
    request: Request,
    body: CommonRequest,
    decrypted: bytes = Depends(decrypt_common_payload),
    db: Session = Depends(get_db),
):
    payload = DeviceSyncPayload.model_validate_json(decrypted)
    existing = db.query(models.Device).filter_by(deviceCode=payload.deviceCode).first()
    data = payload.model_dump()
    if existing:
        for key, value in data.items():
            setattr(existing, key, value)
    else:
        db.add(models.Device(**data))
    db.commit()
    write_audit(db, "device_sync", json.dumps(data, ensure_ascii=False), request.client.host if request.client else None)
    return CommonResponse(resultCode="200", msg="成功")


@router.post("/api/device/dataBatchSync", response_model=CommonResponse)
def data_batch_sync(
    request: Request,
    body: CommonRequest,
    decrypted: bytes = Depends(decrypt_common_payload),
    db: Session = Depends(get_db),
):
    payload = DeviceDataPayload.model_validate_json(decrypted)
    standardized = standardize_device_data(payload.model_dump())
    record = models.DeviceData(
        deviceCode=standardized["deviceCode"],
        messageType=standardized["messageType"],
        reportTime=standardized["reportTime"],
        content=json.dumps(standardized["content"], ensure_ascii=False),
    )
    db.add(record)
    db.commit()
    write_audit(db, "device_data", json.dumps(standardized, ensure_ascii=False), request.client.host if request.client else None)
    return CommonResponse(resultCode="200", msg="成功")
