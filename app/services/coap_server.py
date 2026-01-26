import asyncio
import json
import base64
from datetime import datetime
from pathlib import Path
from aiocoap import resource, Message, Context, Code
from sqlalchemy.orm import Session
from ..db import SessionLocal
from .. import models
from ..config import settings
from ..security.crypto import sm4_gcm_decrypt, now_utc
from .validation import validate_signature, validate_timestamp
from .std_validation import validate_device_data
from ..utils.audit import write_audit


class DataResource(resource.Resource):
    async def render_post(self, request):
        try:
            payload = json.loads(request.payload.decode("utf-8"))
        except Exception:
            return Message(code=Code.BAD_REQUEST, payload=b"invalid payload")
        db: Session = SessionLocal()
        try:
            # 支持加密 envelope（推荐）与明文 payload（兼容）
            if "cipher" in payload and "appkey" in payload and "token" in payload:
                for key in ("appkey", "token", "busId", "cipher", "sign", "timestamp"):
                    if key not in payload:
                        return Message(code=Code.BAD_REQUEST, payload=b"missing fields")
                app = db.query(models.AppCredential).filter_by(appkey=payload["appkey"]).first()
                if not app or app.status != 1:
                    return Message(code=Code.UNAUTHORIZED, payload=b"bad appkey")
                record = db.query(models.TokenRecord).filter_by(token=payload["token"], appkey=payload["appkey"]).first()
                if not record:
                    return Message(code=Code.UNAUTHORIZED, payload=b"bad token")
                if record.expires_at < now_utc():
                    return Message(code=Code.UNAUTHORIZED, payload=b"token expired")
                if not validate_timestamp(int(payload["timestamp"])):
                    return Message(code=Code.BAD_REQUEST, payload=b"bad timestamp")
                if not validate_signature(payload["busId"], payload["cipher"], int(payload["timestamp"]), app.appsecret, payload["sign"]):
                    return Message(code=Code.BAD_REQUEST, payload=b"bad sign")
                sm4_key = base64.b64decode(record.sm4_key_b64)
                decrypted = sm4_gcm_decrypt(payload["cipher"], sm4_key)
                payload_obj = json.loads(decrypted.decode("utf-8"))
            else:
                payload_obj = payload

            base_dir = Path(__file__).resolve().parent.parent.parent
            validate_device_data(base_dir, payload_obj)
            device = db.query(models.Device).filter_by(deviceCode=payload_obj.get("deviceCode")).first()
            if not device:
                return Message(code=Code.NOT_FOUND, payload=b"device not found")

            record = models.DeviceData(
                deviceCode=payload_obj.get("deviceCode", ""),
                messageType=payload_obj.get("messageType", 1),
                reportTime=payload_obj.get("reportTime", ""),
                content=json.dumps(payload_obj.get("content", []), ensure_ascii=False),
                created_at=datetime.utcnow(),
            )
            db.add(record)
            device.last_report_at = datetime.utcnow()
            device.last_message_type = int(payload_obj.get("messageType", 1))
            device.connStatus = 1
            db.commit()
            write_audit(db, "coap_ingest", json.dumps({"path": "iot/data", "deviceCode": record.deviceCode}, ensure_ascii=False), None)
            return Message(code=Code.CREATED, payload=b"ok")
        except Exception:
            db.rollback()
            return Message(code=Code.BAD_REQUEST, payload=b"invalid payload")
        finally:
            db.close()


async def start_coap_server() -> None:
    root = resource.Site()
    root.add_resource(["iot", "data"], DataResource())
    await Context.create_server_context(root, bind=(settings.coap_host, settings.coap_port))
    await asyncio.get_running_loop().create_future()
