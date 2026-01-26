import argparse
import json
import random
import time
from datetime import datetime, timedelta
from uuid import uuid4

import requests

from app.security.crypto import ensure_keypair, rsa_decrypt_sm4_key, sm4_gcm_encrypt, sha256_sign


BASE_URL = "http://127.0.0.1:8000"
APPKEY = "DEMO_APP"
APPSECRET = "DEMO_SECRET"


def get_token() -> str:
    resp = requests.post(f"{BASE_URL}/api/sp-token", json={"appkey": APPKEY}, timeout=10)
    data = resp.json()
    return data["token"]


def build_common_payload(payload: dict, token: str, *, bus_id: str):
    cipher = sm4_gcm_encrypt(json.dumps(payload, ensure_ascii=False).encode("utf-8"), rsa_decrypt_sm4_key(token))
    timestamp = int(time.time() * 1000)
    sign = sha256_sign(bus_id, cipher, timestamp, APPSECRET)
    return {"busId": bus_id, "cipher": cipher, "sign": sign, "timestamp": timestamp}


def _random_device_code(index: int) -> str:
    # 生成 32 位设备编码：便于演示，不代表真实编码规则
    prefix = "0000000100000000"
    suffix = f"{index:016d}"
    return (prefix + suffix)[-32:]


def _random_location():
    # 少量内置样例，避免引入额外依赖
    candidates = [
        ("230000", "黑龙江省", "230800", "佳木斯市", "七星农场", "第一管理区", "132.601522", "47.302815"),
        ("320000", "江苏省", "320100", "南京市", "江宁农场", "第二管理区", "118.845276", "31.936984"),
        ("330000", "浙江省", "330100", "杭州市", "良渚农场", "第三管理区", "120.012343", "30.393221"),
        ("110000", "北京市", "110100", "北京市", "顺义试验田", "试验区", "116.656334", "40.132479"),
    ]
    return random.choice(candidates)


def _build_device_payload(index: int) -> dict:
    provinceCode, provinceName, cityCode, cityName, farmName, managementArea, lng, lat = _random_location()
    return {
        "deviceName": f"气象站{index}号",
        "deviceCode": _random_device_code(index),
        "deviceTypeName": "气象站",
        "manufacturer": "示例厂商",
        "linkType": 1,
        "provinceCode": provinceCode,
        "provinceName": provinceName,
        "cityCode": cityCode,
        "cityName": cityName,
        "farmName": farmName,
        "managementArea": managementArea,
        "lng": lng,
        "lat": lat,
        "state": 1,
        "connStatus": 1,
        "manageStatus": 0,
        "transmissionIntercal": 60,
        "dept": "农业物联网示范",
        "scene1": "v-0",
        "scene2": "v-00",
        "scene3": "v-001",
        "unifiedAddressCode": "330108002020003000590000100",
    }


def _build_device_data_payload(device_code: str, when: datetime) -> dict:
    # updateValue 为字符串以贴近标准字段表现
    temp = round(random.uniform(-15, 35), 1)
    humidity = round(random.uniform(10, 95), 1)
    wind = round(random.uniform(0, 20), 1)
    rainfall = round(max(0, random.gauss(0.5, 1.2)), 2)
    return {
        "deviceCode": device_code,
        "messageType": 1,
        "reportTime": when.strftime("%Y-%m-%d %H:%M:%S"),
        "content": [
            {"topic": "air_temperature", "name": "空气温度", "updateValue": str(temp), "unit": "℃"},
            {"topic": "air_humidity", "name": "空气湿度", "updateValue": str(humidity), "unit": "%"},
            {"topic": "wind_speed", "name": "风速", "updateValue": str(wind), "unit": "m/s"},
            {"topic": "rainfall", "name": "降雨量", "updateValue": str(rainfall), "unit": "mm"},
        ],
    }


def _build_alarm_payload(device_code: str, when: datetime) -> dict:
    return {
        "deviceCode": device_code,
        "alarmCode": "TEMP_HIGH",
        "alarmName": "温度过高",
        "alarmStatus": random.choice([0, 1]),
        "dealTime": when.strftime("%Y-%m-%d %H:%M:%S"),
        "handler": random.choice(["张三", "李四", "王五"]),
        "dept": "运维组",
        "explanation": "演示数据：超过阈值触发告警，已记录处理结果。",
        "enclosures": [{"url": "https://example.com/demo.jpg", "type": 1}],
    }


def main():
    parser = argparse.ArgumentParser(description="生成演示数据（设备、设备数据、告警、交换记录）")
    parser.add_argument("--base-url", default=BASE_URL)
    parser.add_argument("--appkey", default=APPKEY)
    parser.add_argument("--appsecret", default=APPSECRET)
    parser.add_argument("--devices", type=int, default=8, help="生成设备数量")
    parser.add_argument("--points", type=int, default=48, help="每个设备生成的数据点数量")
    parser.add_argument("--alarm-rate", type=float, default=0.15, help="每个数据点触发告警概率")
    args = parser.parse_args()

    global BASE_URL, APPKEY, APPSECRET
    BASE_URL = args.base_url.rstrip("/")
    APPKEY = args.appkey
    APPSECRET = args.appsecret

    # 确保本地存在密钥对（用于解密 token -> SM4 密钥）
    ensure_keypair()

    token = get_token()
    headers = {"token": token, "appkey": APPKEY}

    now = datetime.utcnow()
    for i in range(1, args.devices + 1):
        device_payload = _build_device_payload(i)
        device_common = build_common_payload(device_payload, token, bus_id=f"deviceSync-{uuid4().hex}")
        resp = requests.post(f"{BASE_URL}/api/device/deviceSync", json=device_common, headers=headers, timeout=10)
        resp.raise_for_status()

        device_code = device_payload["deviceCode"]
        for j in range(args.points):
            when = now - timedelta(minutes=(args.points - j - 1) * 10)
            data_payload = _build_device_data_payload(device_code, when)
            data_common = build_common_payload(data_payload, token, bus_id=f"dataBatchSync-{uuid4().hex}")
            resp = requests.post(f"{BASE_URL}/api/device/dataBatchSync", json=data_common, headers=headers, timeout=10)
            resp.raise_for_status()

            if random.random() < args.alarm_rate:
                alarm_payload = _build_alarm_payload(device_code, when)
                alarm_common = build_common_payload(alarm_payload, token, bus_id=f"alarmDealSync-{uuid4().hex}")
                resp = requests.post(f"{BASE_URL}/api/alarm/alarmDealSync", json=alarm_common, headers=headers, timeout=10)
                resp.raise_for_status()

    # 交换能力：中间库 + 消息队列 + 文件
    requests.post(
        f"{BASE_URL}/exchange/middle/push",
        json={"table_name": "demo_events", "payload": {"event": "seed_demo_data", "ts": now.isoformat()}},
        timeout=10,
    )
    try:
        requests.post(
            f"{BASE_URL}/exchange/mq/publish",
            json={"topic": "demo.seed", "payload": {"msg": "seed_demo_data", "ts": now.isoformat()}},
            timeout=10,
        )
    except requests.exceptions.RequestException:
        # RabbitMQ 未启动时允许跳过（其余数据仍可用于前端演示）
        pass
    filename = f"demo-seed-{uuid4().hex[:8]}.txt"
    requests.post(
        f"{BASE_URL}/exchange/file/receive",
        files={"file": (filename, f"seed at {now.isoformat()}".encode("utf-8"), "text/plain")},
        timeout=10,
    )


if __name__ == "__main__":
    main()
