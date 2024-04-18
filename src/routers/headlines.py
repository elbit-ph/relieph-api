from typing import Annotated
from fastapi import APIRouter, Depends

from dependencies import get_db_session, get_logger
from services.db.database import Session
from services.headlines.recent import fetch


router = APIRouter(
    prefix="/headlines",
    tags=["headlines"],
    dependencies=[Depends(get_db_session), Depends(get_logger)]
)

DB = Annotated[Session, Depends(get_db_session)]

@router.get("/recent")
async def recent_headlines(db: DB):
    return fetch(db)