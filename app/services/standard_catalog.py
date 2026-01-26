import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True)
class ParameterSpec:
    英文标识: str
    中文名称: str
    单位: str
    数据类型描述: str
    数据类型编码: int


def _normalize_topic(topic: str) -> str:
    """
    将 topic 归一化为稳定匹配键：
    - 小写
    - 去除括号内容
    - 空白/斜杠等替换为下划线
    - 连续下划线压缩
    """
    s = (topic or "").strip().lower()
    s = re.sub(r"\\(.*?\\)", "", s)
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s


def _parse_data_type_code(data_type_text: str) -> int:
    """
    将标准中类似 `Float(-180~180)`、`Float`、`String` 等类型描述，映射到接口 dataType 编码：
    0-int, 1-bool, 2-string, 3-list, 4-date, 5-long, 6-float, 7-enum
    """
    t = (data_type_text or "").strip().lower()
    if t.startswith("int") or t.startswith("integer"):
        return 0
    if t.startswith("bool"):
        return 1
    if t.startswith("string"):
        return 2
    if t.startswith("list") or t.startswith("array"):
        return 3
    if t.startswith("date") or t.startswith("datetime") or "yyyy" in t:
        return 4
    if t.startswith("long"):
        return 5
    if t.startswith("float") or t.startswith("double"):
        return 6
    if t.startswith("enum"):
        return 7
    # 默认按字符串处理，避免误判导致大量拒绝
    return 2


@lru_cache(maxsize=1)
def load_standard_tables(base_dir: Path) -> dict:
    """
    读取内置的数据字典 JSON（从标准附录表格抽取而来），用于校验与枚举约束。
    注意：本项目不依赖根目录 std.md 文件，统一以 data/data_dictionary.json 为权威输入。
    """
    path = base_dir / "data" / "data_dictionary.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or "tables" not in payload:
        raise ValueError("data/data_dictionary.json 格式不正确")
    return payload


@lru_cache(maxsize=1)
def get_scene_code_triples(base_dir: Path) -> set[tuple[str, str, str]]:
    """
    从表 A.5 解析合法的 (scene1, scene2, scene3) 编码组合。
    """
    tables = load_standard_tables(base_dir).get("tables", [])
    target = None
    for t in tables:
        title = str(t.get("title", ""))
        if "表 A.5" in title and "设备场景编码表" in title:
            target = t
            break
    if not target:
        return set()
    triples: set[tuple[str, str, str]] = set()
    for row in target.get("rows", []):
        if not isinstance(row, list) or len(row) < 6:
            continue
        scene1 = str(row[1]).strip()
        scene2 = str(row[3]).strip()
        scene3 = str(row[5]).strip()
        if scene1 and scene2 and scene3:
            triples.add((scene1, scene2, scene3))
    return triples


@lru_cache(maxsize=1)
def get_disabled_type_codes(base_dir: Path) -> set[int]:
    """
    从表 A.6 解析停用原因编码集合。
    """
    tables = load_standard_tables(base_dir).get("tables", [])
    target = None
    for t in tables:
        title = str(t.get("title", ""))
        if "表 A.6" in title and "停用原因编码表" in title:
            target = t
            break
    if not target:
        return set()
    codes: set[int] = set()
    for row in target.get("rows", []):
        if not isinstance(row, list) or not row:
            continue
        try:
            codes.add(int(str(row[0]).strip()))
        except Exception:
            continue
    return codes


@lru_cache(maxsize=1)
def get_parameter_specs(base_dir: Path) -> dict[str, ParameterSpec]:
    """
    从表 B.* 解析参数英文标识 -> 参数规格，用于运行数据 topic/unit/dataType 的校验。
    返回同时包含：原始英文标识键与归一化键，两者都可命中同一规格。
    """
    tables = load_standard_tables(base_dir).get("tables", [])
    specs: dict[str, ParameterSpec] = {}
    for t in tables:
        title = str(t.get("title", ""))
        if not title.startswith("表 B"):
            continue
        headers = [str(x).strip() for x in (t.get("headers") or [])]
        if not headers:
            continue
        try:
            idx_zh = headers.index("参数名称")
            idx_en = headers.index("英文名称")
            idx_unit = headers.index("单位")
            idx_type = headers.index("数据类型")
        except ValueError:
            # 兜底：按常见顺序解析
            idx_zh, idx_en, idx_unit, idx_type = 1, 2, 3, 4
        idx_category = 0
        last_category = ""

        for raw_row in t.get("rows", []):
            if not isinstance(raw_row, list):
                continue
            row = [str(x).strip() for x in raw_row]
            # 处理 rowspan 导致的缺列：最常见是缺少首列（数据类型分类）
            if len(row) == len(headers) - 1 and idx_category == 0:
                row = [last_category] + row
            if len(row) < max(idx_zh, idx_en, idx_unit, idx_type) + 1:
                continue
            category = row[idx_category] if idx_category < len(row) else ""
            if category:
                last_category = category
            zh_name = row[idx_zh]
            en_name = row[idx_en]
            unit = row[idx_unit]
            data_type_text = row[idx_type]
            if not en_name:
                continue
            spec = ParameterSpec(
                英文标识=en_name,
                中文名称=f"{category}-{zh_name}" if category else zh_name,
                单位=unit,
                数据类型描述=data_type_text,
                数据类型编码=_parse_data_type_code(data_type_text),
            )
            specs[en_name] = spec
            specs[_normalize_topic(en_name)] = spec
    return specs


def match_parameter_spec(base_dir: Path, topic: str) -> ParameterSpec | None:
    """
    根据 topic 查找参数规格：优先精确匹配英文标识，其次使用归一化匹配。
    """
    specs = get_parameter_specs(base_dir)
    if topic in specs:
        return specs[topic]
    key = _normalize_topic(topic)
    return specs.get(key)
