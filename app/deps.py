import base64
from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session
from .db import SessionLocal
from . import models
from .security.crypto import now_utc
from .security.crypto import sm4_gcm_decrypt
from .services.validation import validate_signature, validate_timestamp, ensure_idempotent


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_auth_headers(
    token: str = Header(...),
    appkey: str = Header(...),
):
    return {"token": token, "appkey": appkey}


def require_valid_app_token(
    token: str = Header(...),
    appkey: str = Header(...),
    db: Session = Depends(get_db),
):
    app = db.query(models.AppCredential).filter_by(appkey=appkey).first()
    if not app or app.status != 1:
        raise HTTPException(status_code=401, detail={"resultCode": "403", "msg": "appkey错误"})
    record = db.query(models.TokenRecord).filter_by(token=token, appkey=appkey).first()
    if not record:
        raise HTTPException(status_code=401, detail={"resultCode": "401", "msg": "token错误"})
    if record.expires_at < now_utc():
        raise HTTPException(status_code=401, detail={"resultCode": "402", "msg": "token失效"})
    return {"token": token, "appkey": appkey}


def decrypt_common_payload(
    request: Request,
    headers=Depends(get_auth_headers),
    db: Session = Depends(get_db),
):
    body = getattr(request.state, "body", None) or {}
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail={"resultCode": "405", "msg": "请求参数错误"})
    for required in ("busId", "cipher", "sign", "timestamp"):
        if required not in body:
            raise HTTPException(status_code=400, detail={"resultCode": "405", "msg": "请求参数错误"})
    app = db.query(models.AppCredential).filter_by(appkey=headers["appkey"]).first()
    if not app or app.status != 1:
        raise HTTPException(status_code=401, detail={"resultCode": "403", "msg": "appkey错误"})
    record = db.query(models.TokenRecord).filter_by(token=headers["token"], appkey=headers["appkey"]).first()
    if not record:
        raise HTTPException(status_code=401, detail={"resultCode": "401", "msg": "token错误"})
    if record.expires_at < now_utc():
        raise HTTPException(status_code=401, detail={"resultCode": "402", "msg": "token失效"})
    sm4_key = base64.b64decode(record.sm4_key_b64)
    if not validate_timestamp(body["timestamp"]):
        raise HTTPException(status_code=400, detail={"resultCode": "405", "msg": "请求参数错误"})
    if not validate_signature(body["busId"], body["cipher"], body["timestamp"], app.appsecret, body["sign"]):
        raise HTTPException(status_code=400, detail={"resultCode": "420", "msg": "报文校验不合格"})
    if not ensure_idempotent(db, body["busId"], headers["appkey"]):
        raise HTTPException(status_code=409, detail={"resultCode": "405", "msg": "请求参数错误"})
    try:
        decrypted = sm4_gcm_decrypt(body["cipher"], sm4_key)
    except Exception:
        raise HTTPException(status_code=400, detail={"resultCode": "420", "msg": "报文校验不合格"})
    return decrypted
