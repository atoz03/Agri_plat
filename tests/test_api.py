import json
import time
from uuid import uuid4
from fastapi.testclient import TestClient
from app.main import app
from app.security.crypto import rsa_decrypt_sm4_key, sm4_gcm_encrypt, sha256_sign


def _common(body: dict, *, sm4_key: bytes, appsecret: str):
    cipher = sm4_gcm_encrypt(json.dumps(body, ensure_ascii=False).encode("utf-8"), sm4_key)
    bus_id = f"bus-test-{uuid4().hex}"
    timestamp = int(time.time() * 1000)
    sign = sha256_sign(bus_id, cipher, timestamp, appsecret)
    return {"busId": bus_id, "cipher": cipher, "sign": sign, "timestamp": timestamp}


def test_token_and_device_sync_and_admin_views():
    with TestClient(app) as client:
        resp = client.post("/api/sp-token", json={"appkey": "DEMO_APP"})
        data = resp.json()
        assert data["code"] == "200"
        token = data["token"]
        sm4_key = rsa_decrypt_sm4_key(token)

        # 标准 URL 兼容：/uip-wgateway/iot/{uri}
        resp = client.post("/uip-wgateway/iot/api/sp-token", json={"appkey": "DEMO_APP"})
        assert resp.json()["code"] == "200"
        device_payload = {
            "deviceName": "气象站1号",
            "deviceCode": "00000001000000000502",
            "deviceTypeName": "气象站",
            "manufacturer": "示例厂商",
            "linkType": 1,
            "provinceCode": "230000",
            "provinceName": "黑龙江省",
            "cityCode": "230800",
            "cityName": "佳木斯市",
            "farmName": "七星农场",
            "managementArea": "第一管理区",
            "lng": "132.601522",
            "lat": "47.302815",
            "state": 1,
            "connStatus": 1,
            "manageStatus": 0,
            "transmissionIntercal": 60,
            "dept": "农业物联网示范",
            "scene1": "v-0",
            "scene2": "v-00",
            "scene3": "v-001",
            "unifiedAddressCode": "330108002020003000590000100"
        }
        common = _common(device_payload, sm4_key=sm4_key, appsecret="DEMO_SECRET")
        resp = client.post("/api/device/deviceSync", json=common, headers={"token": token, "appkey": "DEMO_APP"})
        assert resp.json()["resultCode"] == "200"

        resp = client.post(
            "/uip-wgateway/iot/api/device/deviceSync",
            json=_common(device_payload, sm4_key=sm4_key, appsecret="DEMO_SECRET"),
            headers={"token": token, "appkey": "DEMO_APP"},
        )
        assert resp.json()["resultCode"] == "200"

        data_payload = {
            "deviceCode": device_payload["deviceCode"],
            "messageType": 1,
            "reportTime": "2026-01-26 00:00:00",
            "content": [
                {
                    "topic": "Daily minimum air temperature (Tmin)",
                    "name": "每日最低温度",
                    "dataType": 6,
                    "updateValue": "12.3",
                    "unit": "°C",
                },
                {
                    "topic": "Daily precipitation",
                    "name": "每日降雨量",
                    "dataType": 6,
                    "updateValue": "0.5",
                    "unit": "mm",
                },
            ],
        }
        resp = client.post(
            "/api/device/dataBatchSync",
            json=_common(data_payload, sm4_key=sm4_key, appsecret="DEMO_SECRET"),
            headers={"token": token, "appkey": "DEMO_APP"},
        )
        assert resp.json()["resultCode"] == "200"

        alarm_payload = {
            "deviceCode": device_payload["deviceCode"],
            "alarmCode": "TEMP_HIGH",
            "alarmName": "温度过高",
            "alarmStatus": 1,
            "dealTime": "2026-01-26 00:01:00",
            "handler": "张三",
            "dept": "运维组",
            "explanation": "单元测试：演示告警处置同步",
            "enclosures": [{"url": "https://example.com/demo.jpg", "type": 1}],
        }
        resp = client.post(
            "/api/alarm/alarmDealSync",
            json=_common(alarm_payload, sm4_key=sm4_key, appsecret="DEMO_SECRET"),
            headers={"token": token, "appkey": "DEMO_APP"},
        )
        assert resp.json()["resultCode"] == "200"

        headers = {"token": token, "appkey": "DEMO_APP"}
        resp = client.get("/admin/api/summary", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["resultCode"] == "200"

        resp = client.get("/admin/api/devices?page=1&limit=10", headers=headers)
        assert resp.json()["resultCode"] == "200"
        assert resp.json()["total"] >= 1

        resp = client.get(f"/admin/api/device-data?deviceCode={device_payload['deviceCode']}&limit=10", headers=headers)
        assert resp.json()["resultCode"] == "200"
        assert len(resp.json()["items"]) >= 1

        resp = client.get(f"/admin/api/alarm-deals?deviceCode={device_payload['deviceCode']}&limit=10", headers=headers)
        assert resp.json()["resultCode"] == "200"
        assert len(resp.json()["items"]) >= 1
