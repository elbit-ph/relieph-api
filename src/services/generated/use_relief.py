from sqlalchemy import and_
from ..db.models import GenerateRelief

def use_generated_relief(db, id):

    generated_relief_data:GenerateRelief = (
        db.query(GenerateRelief).filter(and_(GenerateRelief.id == id))).first()   

    if generated_relief_data is None:
        return {
            "is_deleted": False,
            "detail": "Generated relief effort not found"
        }
    
    if generated_relief_data.is_used:
        return {
            "is_deleted": False,
            "detail": "Generated relief effort already in use"
        }    

    generated_relief_data.is_used = True
    db.commit()  

    return {
        "is_deleted": True,
        "detail": "Generated relief effort used successfully"
    }