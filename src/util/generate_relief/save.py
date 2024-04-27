import time
import logging
from sqlalchemy import and_
from services.db.models import Headline, GenerateRelief, GeneratedInkind
from services.db.database import Session
from .relief_response import response
from .relief_integrity import relief_data

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_data(db, headline_data, p: int = 1, c: int = 10):
    for data in headline_data:
        try:

            headline_title = data.title
            disaster_type = data.disaster_type
            article_date_posted = data.posted_datetime
            context = data.article

            relief_response = response(disaster_type, headline_title, article_date_posted, context)
            relief_json = relief_data(relief_response)

            generated_relief = GenerateRelief(
                headline_id=data.id,
                relief_title=relief_json['relief_title'],
                description=relief_json['description'],
                monetary_goal=relief_json['monetary_goal'],
                deployment_date=relief_json['deployment_date'],
            )

            db.add(generated_relief)
            db.commit()

            generated_relief_id = db.query(GenerateRelief.id).filter(
                and_(GenerateRelief.headline_id == data.id)).limit(c).offset((p-1)*c).first()

            for item in relief_json['inkind_donation']:

                inkind = GeneratedInkind(
                    generated_relief_id=generated_relief_id[0],
                    item=item['item'],
                    item_desc=item['item_desc'],
                    quantity=item['quantity']
                )

                db.add(inkind)
                db.commit()

            logger.info("Succesfully Added Relief Template Headline!")
            time.sleep(120) 
    
        except Exception as e:
            logger.info("Error in Adding Relief Template Headline!")
            db.rollback()
            # time.sleep(120) 
            continue

def start_gen(p: int = 1, c: int = 10):
    try:
        with Session() as db:

            templated_data = [data[0] for data in db.query(GenerateRelief.headline_id).distinct().limit(c).offset((p-1)*c).all()]

            headline_data = db.query(Headline).filter(~Headline.id.in_(templated_data)).limit(c).offset((p-1)*c).all()

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