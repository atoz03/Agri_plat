import argparse
import json
import random
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

import requests

# 允许从项目根目录直接执行：python scripts/seed_demo_data.py
sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.config import settings
from app.db import SessionLocal, init_db
from app import models
from app.security.crypto import ensure_keypair, rsa_decrypt_sm4_key, sm4_gcm_encrypt, sha256_sign
from app.services.standard_catalog import get_parameter_specs


def _build_common_payload(payload: dict, token: str, *, bus_id: str, appsecret: str) -> dict:
    sm4_key = rsa_decrypt_sm4_key(token)
    cipher = sm4_gcm_encrypt(json.dumps(payload, ensure_ascii=False).encode("utf-8"), sm4_key)
    timestamp = int(time.time() * 1000)
    sign = sha256_sign(bus_id, cipher, timestamp, appsecret)
    return {"busId": bus_id, "cipher": cipher, "sign": sign, "timestamp": timestamp}


def _get_token(base_url: str, appkey: str) -> str:
    resp = requests.post(f"{base_url}/api/sp-token", json={"appkey": appkey}, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != "200" or not data.get("token"):
        raise RuntimeError(f"获取 token 失败：{data}")
    return data["token"]


def _iter_parameter_specs(project_root: Path):
    """
    从内置标准字典中挑选可用于“运行数据上报”的参数集合。
    选择策略：
    - 仅使用 dataType=Float 的参数（便于随机生成）
    - 排除“无单位”项
    """
    specs = get_parameter_specs(project_root)
    uniq = {}
    for spec in specs.values():
        uniq[spec.英文标识] = spec
    candidates = [s for s in uniq.values() if s.数据类型编码 == 6 and s.单位 and s.单位 != "无单位"]
    # 稳定排序，便于复现
    candidates.sort(key=lambda x: x.英文标识)
    return candidates


def _make_device_code(vendor_code: str, seq: int) -> str:
    # 标准：20 位（8 位厂商编码 + 12 位设备自身ID）
    return f"{vendor_code}{seq:012d}"


def seed_via_db(
    *,
    devices: int,
    points_per_day: int,
    days: int,
    alarm_rate: float,
    seed: int,
):
    """
    DB 直写模式：用于大规模造数（默认 1000 台设备、100 条/天）。
    优点：速度快；缺点：不走加密链路。
    """
    random.seed(seed)
    init_db()
    project_root = Path(__file__).resolve().parent.parent
    candidates = _iter_parameter_specs(project_root)
    if len(candidates) < 4:
        raise RuntimeError("标准参数候选不足，无法生成运行数据")

    provinces = [
        ("230000", "黑龙江省", "230800", "佳木斯市", "郊区"),
        ("320000", "江苏省", "320100", "南京市", "江宁区"),
        ("330000", "浙江省", "330100", "杭州市", "余杭区"),
        ("110000", "北京市", "110100", "北京市", "顺义区"),
        ("510000", "四川省", "510100", "成都市", "郫都区"),
    ]
    farms = ["七星农场", "良渚农场", "江宁农场", "顺义试验田", "成都示范田"]
    areas = ["第一管理区", "第二管理区", "第三管理区", "试验区", "示范区"]

    now = datetime.utcnow()
    start = now - timedelta(days=days)
    total_points = devices * points_per_day * days
    print(f"开始造数（DB模式）：devices={devices}, points/day={points_per_day}, days={days}, total_points={total_points}")

    db = SessionLocal()
    try:
        # 设备
        vendor_code = "00000001"
        device_objs = []
        for i in range(1, devices + 1):
            provinceCode, provinceName, cityCode, cityName, county = random.choice(provinces)
            farm = random.choice(farms)
            management = random.choice(areas)
            device_code = _make_device_code(vendor_code, i)
            lng = f"{random.uniform(100, 130):.6f}"
            lat = f"{random.uniform(25, 50):.6f}"
            device_objs.append(
                models.Device(
                    deviceCode=device_code,
                    deviceName=f"气象站{i:04d}号",
                    deviceTypeName="气象站",
                    manufacturer="示例厂商",
                    linkType=1,
                    provinceCode=provinceCode,
                    provinceName=provinceName,
                    cityCode=cityCode,
                    cityName=cityName,
                    farmName=farm,
                    managementArea=management,
                    fieldsName=f"田块{(i % 30) + 1}",
                    lng=lng,
                    lat=lat,
                    state=1,
                    connStatus=1,
                    manageStatus=0,
                    transmissionIntercal=600,  # 10 分钟
                    dept="农业物联网示范",
                    scene1="v-0",
                    scene2="v-00",
                    scene3="v-001",
                    unifiedAddressCode="330108002020003000590000100",
                    last_report_at=now,
                    last_message_type=1,
                )
            )
        # upsert：简化处理，先尝试插入，冲突则逐条更新
        for d in device_objs:
            existing = db.query(models.Device).filter_by(deviceCode=d.deviceCode).first()
            if existing:
                for k, v in d.__dict__.items():
                    if k.startswith("_sa_"):
                        continue
                    setattr(existing, k, v)
            else:
                db.add(d)
        db.commit()

        # 运行数据与告警
        chunk = []
        alarm_chunk = []
        for i in range(1, devices + 1):
            device_code = _make_device_code(vendor_code, i)
            for day in range(days):
                day_start = start + timedelta(days=day)
                for p in range(points_per_day):
                    t = day_start + timedelta(seconds=int((p / points_per_day) * 86400))
                    report_time = t.strftime("%Y-%m-%d %H:%M:%S")
                    # 每条数据带 4 个参数
                    picks = random.sample(candidates, 4)
                    content = []
                    for spec in picks:
                        val = round(random.uniform(0, 100), 2)
                        content.append(
                            {
                                "topic": spec.英文标识,
                                "name": spec.中文名称,
                                "dataType": spec.数据类型编码,
                                "updateValue": str(val),
                                "unit": spec.单位,
                            }
                        )
                    chunk.append(
                        models.DeviceData(
                            deviceCode=device_code,
                            messageType=1,
                            reportTime=report_time,
                            content=json.dumps(content, ensure_ascii=False),
                            created_at=t,
                        )
                    )
                    if random.random() < alarm_rate:
                        alarm_chunk.append(
                            models.AlarmDeal(
                                deviceCode=device_code,
                                alarmCode=f"ALARM-{uuid4().hex[:10]}",
                                alarmName="演示告警",
                                alarmStatus=random.choice([0, 1]),
                                dealTime=report_time,
                                handler=random.choice(["张三", "李四", "王五"]),
                                dept="运维组",
                                explanation="自动生成的演示告警数据",
                                enclosures=None,
                                created_at=t,
                            )
                        )
                    if len(chunk) >= 5000:
                        db.bulk_save_objects(chunk)
                        chunk.clear()
                    if len(alarm_chunk) >= 2000:
                        db.bulk_save_objects(alarm_chunk)
                        alarm_chunk.clear()
        if chunk:
            db.bulk_save_objects(chunk)
        if alarm_chunk:
            db.bulk_save_objects(alarm_chunk)
        db.commit()

        # 交换记录：提供少量示例
        db.add(
            models.MiddleExchangeRecord(
                table_name="demo_events",
                payload=json.dumps({"event": "seed_demo_data", "ts": now.isoformat()}, ensure_ascii=False),
                created_at=now,
            )
        )
        db.add(
            models.MessageQueueRecord(
                topic="demo.seed",
                payload=json.dumps({"msg": "seed_demo_data", "ts": now.isoformat()}, ensure_ascii=False),
                published_at=now,
            )
        )
        db.commit()
    finally:
        db.close()

    print("完成：DB 模式造数完毕。")


def seed_via_api(
    *,
    base_url: str,
    appkey: str,
    appsecret: str,
    devices: int,
    points_per_day: int,
    days: int,
    seed: int,
):
    """
    API 模式：走标准加密链路（适合小规模联调，不建议 1000*100 直接跑）。
    """
    random.seed(seed)
    ensure_keypair()
    project_root = Path(__file__).resolve().parent.parent
    candidates = _iter_parameter_specs(project_root)
    token = _get_token(base_url, appkey)
    headers = {"token": token, "appkey": appkey}

    vendor_code = "00000001"
    now = datetime.utcnow()
    start = now - timedelta(days=days)

    for i in range(1, devices + 1):
        device_code = _make_device_code(vendor_code, i)
        device_payload = {
            "deviceName": f"气象站{i:04d}号",
            "deviceCode": device_code,
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
            "transmissionIntercal": 600,
            "dept": "农业物联网示范",
            "scene1": "v-0",
            "scene2": "v-00",
            "scene3": "v-001",
            "unifiedAddressCode": "330108002020003000590000100",
        }
        common = _build_common_payload(device_payload, token, bus_id=f"deviceSync-{uuid4().hex}", appsecret=appsecret)
        requests.post(f"{base_url}/api/device/deviceSync", json=common, headers=headers, timeout=10).raise_for_status()

        for day in range(days):
            day_start = start + timedelta(days=day)
            for p in range(points_per_day):
                t = day_start + timedelta(seconds=int((p / points_per_day) * 86400))
                report_time = t.strftime("%Y-%m-%d %H:%M:%S")
                picks = random.sample(candidates, 2)
                content = []
                for spec in picks:
                    val = round(random.uniform(0, 100), 2)
                    content.append(
                        {
                            "topic": spec.英文标识,
                            "name": spec.中文名称,
                            "dataType": spec.数据类型编码,
                            "updateValue": str(val),
                            "unit": spec.单位,
                        }
                    )
                data_payload = {"deviceCode": device_code, "messageType": 1, "reportTime": report_time, "content": content}
                common = _build_common_payload(data_payload, token, bus_id=f"dataBatchSync-{uuid4().hex}", appsecret=appsecret)
                requests.post(f"{base_url}/api/device/dataBatchSync", json=common, headers=headers, timeout=10).raise_for_status()

    print("完成：API 模式造数完毕。")


def main():
    parser = argparse.ArgumentParser(description="生成演示数据（默认面向大屏：1000 台设备、100 条/天、10 秒刷新）")
    parser.add_argument("--mode", choices=["db", "api"], default="db", help="造数模式：db=直写数据库（快），api=走加密链路（慢）")
    parser.add_argument("--devices", type=int, default=1000)
    parser.add_argument("--points", type=int, default=100, help="每台设备每天生成的运行数据条数")
    parser.add_argument("--days", type=int, default=1, help="生成多少天的数据（默认 1 天）")
    parser.add_argument("--alarm-rate", type=float, default=0.01, help="每条数据触发告警概率（db 模式生效）")
    parser.add_argument("--seed", type=int, default=20260126)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="api 模式服务地址")
    parser.add_argument("--appkey", default="DEMO_APP")
    parser.add_argument("--appsecret", default="DEMO_SECRET")
    args = parser.parse_args()

    if args.mode == "db":
        seed_via_db(
            devices=args.devices,
            points_per_day=args.points,
            days=args.days,
            alarm_rate=args.alarm_rate,
            seed=args.seed,
        )
        print(f"数据已写入：{settings.db_path}")
        return

    seed_via_api(
        base_url=args.base_url.rstrip("/"),
        appkey=args.appkey,
        appsecret=args.appsecret,
        devices=args.devices,
        points_per_day=args.points,
        days=args.days,
        seed=args.seed,
    )


if __name__ == "__main__":
    main()
