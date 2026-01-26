import asyncio
import json
from aiocoap import resource, Message, Context, Code
from sqlalchemy.orm import Session
from ..db import SessionLocal
from .. import models
from ..config import settings


class DataResource(resource.Resource):
    async def render_post(self, request):
        try:
            payload = json.loads(request.payload.decode("utf-8"))
        except Exception:
            return Message(code=Code.BAD_REQUEST, payload=b"invalid payload")
        db: Session = SessionLocal()
        record = models.DeviceData(
            deviceCode=payload.get("deviceCode", ""),
            messageType=payload.get("messageType", 1),
            reportTime=payload.get("reportTime", ""),
            content=json.dumps(payload.get("content", []), ensure_ascii=False),
        )
        db.add(record)
        db.commit()
        db.close()
        return Message(code=Code.CREATED, payload=b"ok")


async def start_coap_server() -> None:
    root = resource.Site()
    root.add_resource(["iot", "data"], DataResource())
    await Context.create_server_context(root, bind=(settings.coap_host, settings.coap_port))
    await asyncio.get_running_loop().create_future()
