from typing import Annotated
from fastapi import APIRouter, Depends, Response, HTTPException
from dependencies import get_db_session, get_logger
from pydantic import BaseModel
from datetime import datetime

from services.db.models import Headline
from services.db.database import Session
from services.headline_classifier.headline import classified_headlines

router = APIRouter(
    prefix="/headlines",
    tags=["headlines"],
    dependencies=[Depends(get_db_session), Depends(get_logger)]
)

DB = Annotated[Session, Depends(get_db_session)]


@router.post("/save")
async def save_headline_data(db: DB, res: Response):

    try:
        for data in classified_headlines():
            # Convert the string to a datetime object
            posted_datetime = datetime.strptime(data['posted_datetime'], "%Y-%m-%d %H:%M:%S.%f%z")

            headline = Headline(
                title=data['title'],
                link=data['link'],
                disaster_type=data['disaster_type'],
                posted_datetime=posted_datetime
            )

            db.add(headline)

        db.commit()
        return {"detail": "Headline data saved successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
