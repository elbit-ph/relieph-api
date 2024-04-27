from typing import Annotated
from fastapi import APIRouter, Depends

from dependencies import get_db_session, get_logger
from services.db.database import Session
from services.headlines.recent import fetch
from services.generated.relief_template import generated_relief
from services.generated.use_relief import use_generated_relief

router = APIRouter(
    prefix="/headlines",
    tags=["headlines"],
    dependencies=[Depends(get_db_session), Depends(get_logger)]
)

DB = Annotated[Session, Depends(get_db_session)]

@router.get("/recent-disaster")
async def retrieve_disaster_headlines(db: DB, p: int = 1, c: int = 10):
    return fetch(db, p, c)

@router.get("/generated-relief-effort")
async def retrieve_generated_reliefs(db: DB, p: int = 1, c: int = 10):
    return generated_relief(db, p, c)

@router.post("/use-generated-relief-effort/{id}/")
async def retrieve_generated_reliefs(db: DB, id: int):
    return use_generated_relief(db, id)