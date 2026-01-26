import json
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from ..schemas import CommonRequest, CommonResponse, AlarmDealPayload
from ..deps import get_db, decrypt_common_payload
from .. import models
from ..utils.audit import write_audit


router = APIRouter()


@router.post("/api/alarm/alarmDealSync", response_model=CommonResponse)
def alarm_deal_sync(
    request: Request,
    body: CommonRequest,
    decrypted: bytes = Depends(decrypt_common_payload),
    db: Session = Depends(get_db),
):
    payload = AlarmDealPayload.model_validate_json(decrypted)
    record = models.AlarmDeal(
        deviceCode=payload.deviceCode,
        alarmCode=payload.alarmCode,
        alarmName=payload.alarmName,
        alarmStatus=payload.alarmStatus,
        dealTime=payload.dealTime,
        handler=payload.handler,
        dept=payload.dept,
        explanation=payload.explanation,
        enclosures=json.dumps([e.model_dump() for e in payload.enclosures], ensure_ascii=False) if payload.enclosures else None,
    )
    db.add(record)
    db.commit()
    write_audit(db, "alarm_deal", json.dumps(payload.model_dump(), ensure_ascii=False), request.client.host if request.client else None)
    return CommonResponse(resultCode="200", msg="成功")
