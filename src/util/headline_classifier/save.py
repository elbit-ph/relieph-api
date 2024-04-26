import logging
from sqlalchemy import and_
from services.db.models import Headline
from services.db.database import Session
from .scrape_headline import classified_headlines

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_data(db, headline_data):
    for data in headline_data:
        existing_headline = db.query(Headline).filter(
            and_(Headline.link == data['link'])).first()    
        
        if existing_headline:
            continue

        headline = Headline(
            title=data['title'],
            link=data['link'],
            disaster_type=data['disaster_type'],
            posted_datetime=data['posted_datetime']
        )
        
        db.add(headline)
    db.commit()

def start_model():
    try:
        with Session() as db:
            headline_data = classified_headlines()
            add_data(db, headline_data)
    except Exception as e:
        db.rollback()

