from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..schemas import TokenRequest, TokenResponse
from ..db import SessionLocal
from .. import models
from ..security.token import issue_token


router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/api/sp-token", response_model=TokenResponse)
def get_token(payload: TokenRequest, db: Session = Depends(get_db)):
    app = db.query(models.AppCredential).filter_by(appkey=payload.appkey).first()
    if not app or app.status != 1:
        return TokenResponse(code="403", msg="appkey错误")
    token = issue_token(db, payload.appkey)
    return TokenResponse(code="200", msg="成功", token=token)
