import json
from fastapi import APIRouter, Query
from ..config import settings


router = APIRouter()


@router.get("/data/dictionary")
def get_dictionary(table_title: str | None = Query(default=None)):
    path = settings.data_dir / "data_dictionary.json"
    if not path.exists():
        return {"resultCode": "404", "msg": "数据字典未生成"}
    data = json.loads(path.read_text(encoding="utf-8"))
    if table_title:
        tables = [t for t in data["tables"] if table_title in t["title"]]
        return {"resultCode": "200", "msg": "成功", "tables": tables}
    return {"resultCode": "200", "msg": "成功", "tables": data["tables"]}
