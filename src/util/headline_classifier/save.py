import logging
from sqlalchemy import and_
from services.db.models import Headline
from services.db.database import Session
from .scrape_headline import classified_headlines

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

db = Session()

def add_data(db, headline_data):
    for data in headline_data:
        existing_headline = db.query(Headline).filter(
            and_(Headline.link == data['link'])).first()    
        
        if existing_headline:
            logger.info("Duplicate Headline!")
            continue

        if data['disaster_type'] == "non-disaster":
            logger.info("Non-disaster Headline!")
            continue

        headline = Headline(
            title=data['title'],
            link=data['link'],
            disaster_type=data['disaster_type'],
            posted_datetime=data['posted_datetime'],
            article=data['article']
        )
        logger.info("Succesfully Added Headline!")
        db.add(headline)
    db.commit()

def start_model():
    try:
        with Session() as db:
            headline_data = classified_headlines()
            add_data(db, headline_data)
    except Exception as e:
        db.rollback()

# if __name__ == '__main__':
#     add_data(db, headline_data(["https://www.philstar.com/headlines/2023/09/03/2293550/two-dead-over-400000-affected-habagat-due-hanna-goring"]))
#     add_data(db, headline_data(["https://www.philstar.com/headlines/2023/12/04/2316295/magnitude-74-quake-rocks-surigao-del-sur-1-dead"]))
#     add_data(db, headline_data(["https://www.philstar.com/headlines/2020/04/03/2005256/pgh-calls-blood-donation-covid-19-survivors-help-severely-ill-patients"]))
#     add_data(db, headline_data(["https://www.philstar.com/headlines/2017/07/01/1715342/groups-provide-feeding-program-marawi-students-displaced-war?nomobile=1"]))
#     add_data(db, headline_data(["https://www.philstar.com/headlines/2023/09/23/2298471/122-calabarzon-residents-fall-ill-due-taal-volcanic-smog"]))
#     add_data(db, headline_data(["https://www.philstar.com/the-freeman/cebu-news/2023/12/13/2318532/biggest-hit-lapu-lapu-city-fire-leaves-thousands-homeless"]))