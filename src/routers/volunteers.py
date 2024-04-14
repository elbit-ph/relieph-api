from typing import Annotated
from fastapi import APIRouter, Depends, UploadFile, HTTPException, status, Response, Body
from dependencies import get_db_session, get_logger, get_current_user
from services.db.database import Session
from services.db.models import Volunteer, VolunteerRequirement, ReliefEffort, User, Address
from services.log.log_handler import LoggingService
from models.auth_details import AuthDetails
from util.auth.auth_tool import authorize
from sqlalchemy import and_
from util.auth.jwt_util import (
    get_hashed_password
)
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(
    prefix="/volunteers",
    tags=["volunteers"],
    dependencies=[Depends(get_db_session), Depends(get_logger)]
)

DB = Annotated[Session, Depends(get_db_session)]
Logger = Annotated[LoggingService, Depends(get_logger)]

@router.get("/{id}")
def retrieveVolunteers(db:DB, id:int, p: int = 1, c: int = 10):
    reliefEffort:ReliefEffort = db.query(ReliefEffort).filter(and_(ReliefEffort.id == id, ReliefEffort.is_deleted == False)).first()

    if reliefEffort is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Relief effort not found."
        )
    volunteer:Volunteer = db.query(Volunteer).filter(Volunteer.relief_id == id).all()
    return volunteer

class VolunteerRequirementsDTO(BaseModel):
    name:str
    description:str
    count:int
    duration_days:int

@router.post("/{id}")
def createVolunteerRequirements(body:VolunteerRequirementsDTO, db:DB, res:Response, id: int):
    
    volunteerRequirement:VolunteerRequirement = db.query(VolunteerRequirement).filter(and_(VolunteerRequirement.name == body.name, VolunteerRequirement.is_deleted == False)).first()

    if volunteerRequirement is not None:
        res.status_code = 400
        return {"detail": "Name already exists"}
    
    volunteerRequirement = VolunteerRequirement()

    volunteerRequirement.relief_id = id
    volunteerRequirement.name = body.name
    volunteerRequirement.description = body.description
    volunteerRequirement.count = body.count
    volunteerRequirement.duration_days = body.duration_days

    db.add(volunteerRequirement)
    db.commit()

    volunteerRequirement = db.query(VolunteerRequirement).filter(VolunteerRequirement.name == body.name).first()

    return {"details": "Organization created.",
            "volunteer_requirements_id": volunteerRequirement.id}

@router.patch("/{id}")
def editVolunteerRequirements(body:VolunteerRequirementsDTO, db:DB, res:Response, id: int):
    volunteerRequirement:VolunteerRequirement = db.query(VolunteerRequirement).filter(and_(VolunteerRequirement.name == body.name, VolunteerRequirement.is_deleted == False)).first()

    if volunteerRequirement is None:
        res.status_code = 404
        return {"detail": "Volunteer requirements non-existent"}
    
    volunteerRequirement.name = volunteerRequirement.name if body.name is "" else body.name
    volunteerRequirement.description = volunteerRequirement.ndescriptioname if body.description is "" else body.description
    volunteerRequirement.count = volunteerRequirement.count if body.count is "" else body.count
    volunteerRequirement.duration_days = volunteerRequirement.duration_days if body.duration_days is "" else body.duration_days
    volunteerRequirement.updated_at = datetime.now()

    db.commit()

    return {"detail": "Volunteer requirements successfully updated."}

@router.post("/{id}/apply")
def applyAsVolunteer(id:int, res:Response, db:DB, user:AuthDetails = Depends(get_current_user)):
    volunteerRequirement:VolunteerRequirement = db.query(VolunteerRequirement).filter(and_(VolunteerRequirement.relief_id == id, VolunteerRequirement.is_deleted == False)).first()
    
    if volunteerRequirement is None:
        res.status_code = 404
        return {"detail": "Relief effort not found."}
    
    volunteer:Volunteer = db.query(Volunteer).filter(Volunteer.volunteer_id == user.user_id).first()

    if volunteer is not None:
        res.status_code = 400
        return {"detail": "Is already a volunteer."}
    
    volunteer = Volunteer()

    volunteer.volunteer_id = user.user_id
    volunteer.volunteer_requirement_id = volunteerRequirement.id
    volunteer.relief_id = id

    db.add(volunteer)
    db.commit()

    volunteer = db.query(Volunteer).filter(Volunteer.volunteer_id == user.user_id).first()

    return {"details": "Successfully applied as a volunteer.",
            "volunteer_id" : volunteer.id}

@router.patch("/{id}/approve/{user_id}")
def approveApplication (id:int, user_id:int, db:DB, res:Response):
    volunteerRequirement:VolunteerRequirement = db.query(VolunteerRequirement).filter(and_(VolunteerRequirement.relief_id == id, VolunteerRequirement.is_deleted == False)).first()

    if volunteerRequirement is None:
        res.status_code = 404
        return {"detail": "Relief effort not found."}
    
    volunteer:Volunteer = db.query(Volunteer).filter(Volunteer.volunteer_id == user_id).first()

    if volunteer is None:
        res.status_code = 404
        return {"detail": "User not found."}
    
    volunteer.status = 'APPROVED'

    db.commit()
    #missing feature - send notification through email

    return {"detail": "Volunteer approved."}

@router.patch("/{id}/approve/{user_id}")
def rejectApplication (id:int, user_id:int, db:DB, res:Response):
    volunteerRequirement:VolunteerRequirement = db.query(VolunteerRequirement).filter(and_(VolunteerRequirement.relief_id == id, VolunteerRequirement.is_deleted == False)).first()

    if volunteerRequirement is None:
        res.status_code = 404
        return {"detail": "Relief effort not found."}
    
    volunteer:Volunteer = db.query(Volunteer).filter(Volunteer.volunteer_id == user_id).first()

    if volunteer is None:
        res.status_code = 404
        return {"detail": "User not found."}
    
    volunteer.status = 'REJECTED'

    db.commit()
    #missing feature - send notification through email

    return {"detail": "Volunteer rejected."}

@router.delete("/{id}/remove/{user_id}")
def removeApplication (id:int, user_id:int, db:DB, res:Response):
    volunteerRequirement:VolunteerRequirement = db.query(VolunteerRequirement).filter(and_(VolunteerRequirement.relief_id == id, VolunteerRequirement.is_deleted == False)).first()

    if volunteerRequirement is None:
        res.status_code = 404
        return {"detail": "Relief effort not found."}
    
    volunteer:Volunteer = db.query(Volunteer).filter(Volunteer.volunteer_id == user_id).first()

    if volunteer is None:
        res.status_code = 404
        return {"detail": "User not found."}
    
    volunteer.is_deleted = True

    db.commit()
    #missing feature - send notification through email

    return {"detail": "Volunteer removed."}

