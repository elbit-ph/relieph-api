from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException

from dependencies import get_db_session
from services.db.database import Session
from services.db.models import User

router = APIRouter(
    prefix="/test",
    tags=["test"],
    dependencies=[Depends(get_db_session)]
)

DB = Annotated[Session, Depends(get_db_session)]

@router.get("/")
async def get_test():
    return {"message":"Hello World!"}

@router.get("/db-tests")
async def get_db(db: DB):
    return {"user count": db.query(User).all()}