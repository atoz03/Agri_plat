import re
from datetime import datetime
from pathlib import Path

from fastapi import HTTPException

from .standard_catalog import get_disabled_type_codes, get_scene_code_triples, match_parameter_spec


_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATETIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")


def _raise(result_code: str, msg: str, *, status_code: int = 400) -> None:
    raise HTTPException(status_code=status_code, detail={"resultCode": result_code, "msg": msg})


def validate_device_code(device_code: str) -> None:
    # 标准：20 位（8 位厂商编码 + 12 位设备自身ID），此处按“20 位数字”校验
    if not device_code or not device_code.isdigit() or len(device_code) != 20:
        _raise("421", "请求内容错误：deviceCode 不符合 20 位编码规则")


def validate_scene_codes(base_dir: Path, scene1: str, scene2: str, scene3: str) -> None:
    triples = get_scene_code_triples(base_dir)
    if not triples:
        return
    if (scene1, scene2, scene3) not in triples:
        _raise("421", "请求内容错误：设备场景编码不在标准表 A.5 范围内")


def validate_device_sync(base_dir: Path, payload: dict) -> None:
    validate_device_code(str(payload.get("deviceCode", "")))

    scene1 = str(payload.get("scene1", "")).strip()
    scene2 = str(payload.get("scene2", "")).strip()
    scene3 = str(payload.get("scene3", "")).strip()
    if scene1 and scene2 and scene3:
        validate_scene_codes(base_dir, scene1, scene2, scene3)

    state = payload.get("state")
    if state not in (1, -1):
        _raise("405", "请求参数错误：state 仅支持 1/-1")

    manage_status = payload.get("manageStatus")
    if manage_status not in (0, 1):
        _raise("405", "请求参数错误：manageStatus 仅支持 0/1")

    if manage_status == 1:
        disabled_type = payload.get("disabledType")
        if disabled_type is None:
            _raise("421", "请求内容错误：manageStatus=1 时 disabledType 必填")
        try:
            disabled_type_int = int(disabled_type)
        except Exception:
            _raise("405", "请求参数错误：disabledType 必须为整数")
        codes = get_disabled_type_codes(base_dir)
        if codes and disabled_type_int not in codes:
            _raise("421", "请求内容错误：disabledType 不在标准表 A.6 范围内")

    production_date = payload.get("productionDate")
    if production_date and not _DATE_RE.match(str(production_date)):
        _raise("405", "请求参数错误：productionDate 格式应为 YYYY-MM-DD")
    install_date = payload.get("installDate")
    if install_date and not _DATE_RE.match(str(install_date)):
        _raise("405", "请求参数错误：installDate 格式应为 YYYY-MM-DD")

    # 经纬度格式：至少 6 位小数（标准要求精度至少到小数点后六位）
    for key in ("lng", "lat"):
        val = str(payload.get(key, "")).strip()
        if not val or "." not in val:
            _raise("405", f"请求参数错误：{key} 格式不正确")
        frac = val.split(".", 1)[1]
        if len(frac) < 6:
            _raise("405", f"请求参数错误：{key} 精度至少到小数点后六位")

    intercal = payload.get("transmissionIntercal")
    try:
        intercal_int = int(intercal)
    except Exception:
        _raise("405", "请求参数错误：transmissionIntercal 必须为整数")
    if intercal_int <= 0:
        _raise("405", "请求参数错误：transmissionIntercal 必须大于 0")


def validate_device_data(base_dir: Path, payload: dict) -> None:
    validate_device_code(str(payload.get("deviceCode", "")))

    message_type = payload.get("messageType")
    if message_type not in (1, 2, 3, 4):
        _raise("405", "请求参数错误：messageType 仅支持 1/2/3/4")

    report_time = str(payload.get("reportTime", "")).strip()
    if not _DATETIME_RE.match(report_time):
        _raise("405", "请求参数错误：reportTime 格式应为 YYYY-MM-DD HH:mm:ss")
    # 解析一次，避免明显非法日期穿透
    try:
        datetime.strptime(report_time, "%Y-%m-%d %H:%M:%S")
    except Exception:
        _raise("405", "请求参数错误：reportTime 不合法")

    content = payload.get("content")
    if message_type == 4:
        # 心跳可不带内容，仅用于保活
        return
    if not isinstance(content, list) or not content:
        _raise("421", "请求内容错误：content 必须为非空列表")

    for item in content:
        if not isinstance(item, dict):
            _raise("421", "请求内容错误：content 元素必须为对象")
        topic = str(item.get("topic", "")).strip()
        name = str(item.get("name", "")).strip()
        if not topic or not name:
            _raise("421", "请求内容错误：topic/name 必填")

        if message_type == 1:
            if item.get("dataType") is None:
                _raise("421", "请求内容错误：messageType=1 时 dataType 必填")
            if item.get("updateValue") is None:
                _raise("421", "请求内容错误：messageType=1 时 updateValue 必填")
            unit = str(item.get("unit", "")).strip()
            if unit is None or unit == "":
                _raise("421", "请求内容错误：messageType=1 时 unit 必填")

            spec = match_parameter_spec(base_dir, topic)
            if not spec:
                _raise("422", f"传输数据验证不正确：topic 不在标准附录B范围内（{topic}）")
            try:
                data_type = int(item.get("dataType"))
            except Exception:
                _raise("405", "请求参数错误：dataType 必须为整数")
            if data_type != spec.数据类型编码:
                _raise("422", f"传输数据验证不正确：dataType 与标准不一致（{topic}）")
            if spec.单位 and unit != spec.单位:
                _raise("422", f"传输数据验证不正确：unit 与标准不一致（{topic}）")

        else:
            # 告警/故障：要求 alarmCode/alarmType/alarmLevel
            if not str(item.get("alarmCode", "")).strip():
                _raise("421", "请求内容错误：messageType=2/3 时 alarmCode 必填")
            if item.get("alarmType") is None or item.get("alarmLevel") is None:
                _raise("421", "请求内容错误：messageType=2/3 时 alarmType/alarmLevel 必填")


def validate_alarm_deal(payload: dict) -> None:
    validate_device_code(str(payload.get("deviceCode", "")))
    if not str(payload.get("alarmCode", "")).strip():
        _raise("421", "请求内容错误：alarmCode 必填")

    deal_time = str(payload.get("dealTime", "")).strip()
    if not _DATETIME_RE.match(deal_time):
        _raise("405", "请求参数错误：dealTime 格式应为 YYYY-MM-DD HH:mm:ss")


def validate_search_addr_where(where: list[dict]) -> None:
    # 标准：city、county 为必传查询条件
    keys = {str(r.get("key", "")).strip() for r in where if isinstance(r, dict)}
    if "city" not in keys or "county" not in keys:
        _raise("421", "请求内容错误：where 中 city、county 为必传查询条件")
