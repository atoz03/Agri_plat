import json
import base64
from pathlib import Path
from datetime import datetime
from sqlalchemy.orm import Session
import paho.mqtt.client as mqtt
from ..config import settings
from ..db import SessionLocal
from .. import models
from ..security.crypto import sm4_gcm_decrypt, now_utc
from .validation import validate_signature, validate_timestamp
from .std_validation import validate_device_data
from ..utils.audit import write_audit


def _decrypt_envelope(db: Session, envelope: dict) -> dict:
    """
    MQTT/CoAP 场景下无法使用 HTTP Header，约定 envelope 字段：
    - appkey, token
    - busId, cipher, sign, timestamp
    解密后得到标准业务 payload（等价于 HTTP 接口 body 解密结果）。
    """
    for key in ("appkey", "token", "busId", "cipher", "sign", "timestamp"):
        if key not in envelope:
            raise ValueError("缺少必要字段")
    app = db.query(models.AppCredential).filter_by(appkey=envelope["appkey"]).first()
    if not app or app.status != 1:
        raise ValueError("appkey错误")
    record = db.query(models.TokenRecord).filter_by(token=envelope["token"], appkey=envelope["appkey"]).first()
    if not record:
        raise ValueError("token错误")
    if record.expires_at < now_utc():
        raise ValueError("token失效")
    if not validate_timestamp(int(envelope["timestamp"])):
        raise ValueError("timestamp错误")
    if not validate_signature(envelope["busId"], envelope["cipher"], int(envelope["timestamp"]), app.appsecret, envelope["sign"]):
        raise ValueError("签名错误")
    sm4_key = base64.b64decode(record.sm4_key_b64)
    decrypted = sm4_gcm_decrypt(envelope["cipher"], sm4_key)
    return json.loads(decrypted.decode("utf-8"))


def _handle_message(topic: str, payload: str) -> None:
    data = json.loads(payload)
    db: Session = SessionLocal()
    try:
        # topic 规则：{prefix}/{deviceCode}/{messageType}
        parts = topic.split("/")
        if len(parts) >= 3 and parts[0] == settings.mqtt_topic_prefix:
            data.setdefault("deviceCode", parts[1])
            try:
                data.setdefault("messageType", int(parts[2]))
            except Exception:
                pass

        # 支持加密 envelope（推荐）与明文 payload（兼容）
        if "cipher" in data and "appkey" in data and "token" in data:
            payload_obj = _decrypt_envelope(db, data)
        else:
            payload_obj = data

        base_dir = Path(__file__).resolve().parent.parent.parent
        validate_device_data(base_dir, payload_obj)

        device = db.query(models.Device).filter_by(deviceCode=payload_obj.get("deviceCode")).first()
        if not device:
            return

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
        write_audit(db, "mqtt_ingest", json.dumps({"topic": topic, "deviceCode": record.deviceCode}, ensure_ascii=False), None)
    except Exception:
        db.rollback()
    finally:
        db.close()


def run_mqtt_ingest() -> None:
    client = mqtt.Client()

    def on_connect(client_obj, userdata, flags, rc):
        topic = f"{settings.mqtt_topic_prefix}/+/+"
        client_obj.subscribe(topic, qos=1)

    def on_message(client_obj, userdata, msg):
        try:
            _handle_message(msg.topic, msg.payload.decode("utf-8"))
        except Exception:
            pass

    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(settings.mqtt_broker_host, settings.mqtt_broker_port, 60)
    client.loop_forever()
