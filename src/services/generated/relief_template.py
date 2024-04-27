from typing import List
from sqlalchemy import and_
from ..headlines.recent import retrieveHeadlineData
from ..db.models import GenerateRelief, GeneratedInkind

WEEKS = 400

def generated_relief(db, p, c):
    results = []

    headline_data = retrieveHeadlineData(db)
    for data in headline_data:
        headline_id = data.id

        generated_relief_data:List[GenerateRelief] = (
        db.query(GenerateRelief).filter(and_(GenerateRelief.headline_id == headline_id)).limit(c).offset((p-1)*c).all())    

        for relief in generated_relief_data:

            generated_data = dict_relief(data, relief)
            inkind_data = db.query(GeneratedInkind).filter(GeneratedInkind.generated_relief_id == relief.id).limit(c).offset((p-1)*c).all()

            for inkind in inkind_data:
                generated_data["inkind_donation"].append({
                    "item": inkind.item,
                    "item_desc": inkind.item_desc,
                    "quantity": inkind.quantity
                })

            results.append(generated_data)

    return results

def dict_relief(data, relief):
    relief_data = {
        "disaster_type": data.disaster_type,
        "relief_title": relief.relief_title,
        "description": relief.description,
        "headline_title": data.title,
        "date_posted": data.posted_datetime,
        "link": data.link,
        "monetary_goal": relief.monetary_goal,
        "inkind_donation": [],
        "deployment_date": relief.deployment_date,
        "is_used": relief.is_used
    }

    return relief_data