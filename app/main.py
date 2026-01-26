import json
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from .config import settings
from .db import init_db, SessionLocal
from .security.crypto import ensure_keypair
from . import models
from .routers import auth, device, alarm, address, exchange, data_dictionary, admin


app = FastAPI(title="农业物联网大田环境感知数据接入平台 Demo")

ui_dir = Path(__file__).resolve().parent / "static" / "ui"
if ui_dir.exists():
    app.mount("/ui", StaticFiles(directory=str(ui_dir), html=True), name="ui")

# 文件 HTTP 服务/共享访问（标准 9.2.5/9.2.6 演示）：只读挂载交换目录
exchange_dir = settings.data_dir / "exchange"
exchange_dir.mkdir(parents=True, exist_ok=True)
app.mount("/exchange/files", StaticFiles(directory=str(exchange_dir), html=False), name="exchange_files")


@app.get("/", include_in_schema=False)
def root():
    if ui_dir.exists():
        return RedirectResponse(url="/ui")
    return {"resultCode": "200", "msg": "成功"}


@app.middleware("http")
async def capture_body(request: Request, call_next):
    if request.method == "POST" and request.url.path != "/api/sp-token":
        try:
            body = await request.json()
            request.state.body = body
        except Exception:
            return JSONResponse(status_code=400, content={"resultCode": "405", "msg": "请求参数错误"})
    response = await call_next(request)
    return response


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if isinstance(exc.detail, dict):
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    return JSONResponse(status_code=exc.status_code, content={"resultCode": "500", "msg": "服务器内部错误"})


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"resultCode": "500", "msg": "服务器内部错误"})


@app.on_event("startup")
def on_startup():
    ensure_keypair()
    init_db()
    db = SessionLocal()
    default_app = db.query(models.AppCredential).filter_by(appkey="DEMO_APP").first()
    if not default_app:
        db.add(models.AppCredential(appkey="DEMO_APP", appsecret="DEMO_SECRET", status=1))
        db.commit()
    db.close()


app.include_router(auth.router)
app.include_router(device.router)
app.include_router(alarm.router)
app.include_router(address.router)
app.include_router(exchange.router)
app.include_router(data_dictionary.router)
app.include_router(admin.router)

# 标准 URL 兼容：/uip-wgateway/iot/{uri}
app.include_router(auth.router, prefix="/uip-wgateway/iot", include_in_schema=False)
app.include_router(device.router, prefix="/uip-wgateway/iot", include_in_schema=False)
app.include_router(alarm.router, prefix="/uip-wgateway/iot", include_in_schema=False)
app.include_router(address.router, prefix="/uip-wgateway/iot", include_in_schema=False)
