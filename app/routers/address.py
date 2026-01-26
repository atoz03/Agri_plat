import json
from pathlib import Path
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from ..schemas import CommonRequest
from ..deps import get_db, decrypt_common_payload
from ..services.validation import parse_where
from ..services.std_validation import validate_search_addr_where
from ..config import settings


router = APIRouter()


@router.post("/api/zfw/searchAddr")
def search_address(
    request: Request,
    body: CommonRequest,
    decrypted: bytes = Depends(decrypt_common_payload),
    db: Session = Depends(get_db),
):
    payload = json.loads(decrypted.decode("utf-8"))
    where = parse_where(payload.get("where", []))
    validate_search_addr_where(where)
    catalog_path = settings.data_dir / "address_catalog.json"
    items = json.loads(catalog_path.read_text(encoding="utf-8")) if catalog_path.exists() else []
    def match(item):
        for rule in where:
            key = rule.get("key")
            value = rule.get("value")
            if key and value and str(item.get(key)) != str(value):
                return False
        if payload.get("equal"):
            return item.get("sourceaddress") == payload.get("addr")
        return payload.get("addr") in item.get("sourceaddress", "")
    filtered = [i for i in items if match(i)]
    page = int(payload.get("page", 1))
    limit = int(payload.get("limit", 10))
    start = (page - 1) * limit
    end = start + limit
    content = filtered[start:end]
    total = len(filtered)
    total_pages = (total + limit - 1) // limit if limit else 1
    return {
        "resultCode": "200",
        "msg": "成功",
        "totalPages": total_pages,
        "totalElements": total,
        "limit": limit,
        "NumberOfElements": len(content),
        "page": page,
        "content": content,
    }
