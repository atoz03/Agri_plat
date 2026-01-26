import json
from sqlalchemy.orm import Session
import paho.mqtt.client as mqtt
from ..config import settings
from ..db import SessionLocal
from .. import models


def _handle_message(payload: str) -> None:
    data = json.loads(payload)
    db: Session = SessionLocal()
    record = models.DeviceData(
        deviceCode=data.get("deviceCode", ""),
        messageType=data.get("messageType", 1),
        reportTime=data.get("reportTime", ""),
        content=json.dumps(data.get("content", []), ensure_ascii=False),
    )
    db.add(record)
    db.commit()
    db.close()


def run_mqtt_ingest() -> None:
    client = mqtt.Client()

    def on_connect(client_obj, userdata, flags, rc):
        topic = f"{settings.mqtt_topic_prefix}/+/+"
        client_obj.subscribe(topic, qos=1)

    def on_message(client_obj, userdata, msg):
        try:
            _handle_message(msg.payload.decode("utf-8"))
        except Exception:
            pass

    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(settings.mqtt_broker_host, settings.mqtt_broker_port, 60)
    client.loop_forever()
