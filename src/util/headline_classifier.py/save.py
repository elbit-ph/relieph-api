import asyncio

from fastapi import Depends
from typing import Annotated

from scrape_headline import classified_headlines
from services.db.models import Headline
from services.db.database import Session
from dependencies import get_db_session


def save_headline_data(db):
    headline_data = classified_headlines()
    for data in headline_data:

        headline = Headline(
            title=data['title'],
            link=data['link'],
            disaster_type=data['disaster_type'],
            posted_datetime=data['posted_datetime']
        )

        db.add(headline)

    db.commit()

async def start_model():
    db = Annotated[Session, Depends(get_db_session)]

    while True:
        await save_headline_data(db)
        await asyncio.sleep(600)