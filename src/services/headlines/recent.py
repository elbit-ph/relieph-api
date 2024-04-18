from typing import List
from sqlalchemy import and_
from datetime import datetime, timedelta
from ..db.models import Headline
from ..db.database import Session

def retrieveHeadlineData(db):
    current_datetime = datetime.now()
    two_weeks = current_datetime + timedelta(weeks=2)

    headline_data: List[Headline] = (
        db.query(Headline).filter(
            and_(
                Headline.disaster_type != 'non-disaster',
                Headline.posted_datetime < two_weeks
            )).all())    

    return headline_data

def fetch(db):
    headlines = []
    headline_data = retrieveHeadlineData(db)

    for data in headline_data:

        headline = {
            'title' : data.title,
            'link' : data.link,
            'disaster_type' : data.disaster_type,
            'posted_datetime' : data.posted_datetime
        }

        headlines.append(headline)
    
    return headlines