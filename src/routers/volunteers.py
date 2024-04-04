from typing import Annotated, List
from fastapi import APIRouter, Depends, UploadFile, HTTPException, status, Response, Body
from dependencies import get_db_session, get_logger, get_s3_handler, get_current_user
from services.db.database import Session
from services.db.models import Volunteer, VolunteerRequirement, ReliefEffort, User, Address, Organization
from services.log.log_handler import LoggingService
from services.aws.s3_handler import S3_Handler
from models.auth_details import AuthDetails
from util.auth.auth_tool import authorize
from sqlalchemy import and_
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(
    prefix="/volunteers",
    tags=["volunteers"],
    dependencies=[Depends(get_db_session), Depends(get_logger)]
)

DB = Annotated[Session, Depends(get_db_session)]
Logger = Annotated[LoggingService, Depends(get_logger)]
S3Handler = Annotated[S3_Handler, Depends(get_s3_handler)]

@router.get("/{id}")
def retrieveVolunteers(id:int, db:DB, res:Response, type:str = 'ALL', user: AuthDetails = Depends(get_current_user)):
    authorize(user, 2, 4)
    
    reliefEffort:ReliefEffort = db.query(ReliefEffort).filter(and_(ReliefEffort.id == id, ReliefEffort.is_deleted == False)).first()

    if reliefEffort is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Relief effort not found."
        )
    
    # check if user is authorized to view volunteer list
    authorized = True
    
    if user.level == 4:
        # admins can view this easily
        authorized == True
    elif reliefEffort.owner_type == 'USER':
        if reliefEffort.owner_id != user.user_id:
            authorized == False
    else:
        org:Organization = db.query(Organization).filter(Organization.id == reliefEffort.owner_id).first()
        if user.user_id != org.owner_id:
            authorized == False
        
    if authorized == False:
        if reliefEffort.owner_id != user.user_id:
            res.status_code = 403
            return {'detail' : 'Insufficient authorization to access volunteers list.'}
    
    volunteers:List[Volunteer] = List[Volunteer]
    if type == 'APPROVED':
        volunteers = db.query(Volunteer).filter(Volunteer.relief_id == id, Volunteer.status == 'APPROVED').all()
    elif type == 'REJECTED':
        volunteers = db.query(Volunteer).filter(Volunteer.relief_id == id, Volunteer.status == 'REJECTED').all()
    elif type == 'PENDING':
        volunteers = db.query(Volunteer).filter(Volunteer.relief_id == id, Volunteer.status == 'PENDING').all()
    else:
        volunteers = db.query(Volunteer).filter(Volunteer.relief_id == id).all()
    return volunteers

# endpoint that gets volunteer requirements for a relief
# - place this in relief effort api

class VolunteerRequirementsDTO(BaseModel):
    name:str
    description:str
    count:int
    duration_days:int

@router.post("/{id}")
def add_volunter_requirement(body:VolunteerRequirementsDTO, db:DB, res:Response, id: int, user: AuthDetails = Depends(get_current_user)):
    authorize(user, 2, 4)

    reliefEffort:ReliefEffort = db.query(ReliefEffort).filter(and_(ReliefEffort.id == id, ReliefEffort.is_deleted == False, ReliefEffort.is_active == True)).first()

    if reliefEffort is None:
        res.status_code = 404
        return {'detail' : 'Relief effort not found.'}
    
    authorized = True
    
    if user.level == 4:
        # admins can view this easily
        authorized == True
    elif reliefEffort.owner_type == 'USER':
        if reliefEffort.owner_id != user.user_id:
            authorized == False
    else:
        org:Organization = db.query(Organization).filter(Organization.id == reliefEffort.owner_id).first()
        if user.user_id != org.owner_id:
            authorized == False
    
    if authorized == False:
        if reliefEffort.owner_id != user.user_id:
            res.status_code = 403
            return {'detail' : 'Insufficient authorization to add volunteer requirements.'}

    volunteerRequirement:VolunteerRequirement = db.query(VolunteerRequirement).filter(and_(VolunteerRequirement.name == body.name, VolunteerRequirement.is_deleted == False)).first()

    if volunteerRequirement is not None:
        res.status_code = 400
        return {"detail": "Requirement already exists"}
    
    volunteerRequirement = VolunteerRequirement()

    volunteerRequirement.relief_id = id
    volunteerRequirement.name = body.name
    volunteerRequirement.description = body.description
    volunteerRequirement.count = body.count
    volunteerRequirement.duration_days = body.duration_days

    db.add(volunteerRequirement)
    db.commit()

    return {"details": "Volunteer requirement created."}

# create new endpoint that creates

## Temporarily commented out - may not yet be needed
# @router.patch("/{id}")
# def editVolunteerRequirements(body:VolunteerRequirementsDTO, db:DB, res:Response, id: int):
#     volunteerRequirement:VolunteerRequirement = db.query(VolunteerRequirement).filter(and_(VolunteerRequirement.name == body.name, VolunteerRequirement.is_deleted == False)).first()

#     if volunteerRequirement is None:
#         res.status_code = 404
#         return {"detail": "Volunteer requirements non-existent"}
    
#     volunteerRequirement.name = volunteerRequirement.name if body.name is "" else body.name
#     volunteerRequirement.description = volunteerRequirement.ndescriptioname if body.description is "" else body.description
#     volunteerRequirement.count = volunteerRequirement.count if body.count is "" else body.count
#     volunteerRequirement.duration_days = volunteerRequirement.duration_days if body.duration_days is "" else body.duration_days
#     volunteerRequirement.updated_at = datetime.now()

#     db.commit()

#     return {"detail": "Volunteer requirements successfully updated."}

# take note: Id here is volunteer requirement id
@router.post("/{id}/apply")
def applyAsVolunteer(id:int, res:Response, db:DB, user:AuthDetails = Depends(get_current_user)):
    authorize(user, 1, 4)

    volunteerRequirement:VolunteerRequirement = db.query(VolunteerRequirement).filter(and_(VolunteerRequirement.relief_id == id, VolunteerRequirement.is_deleted == False)).first()
    
    if volunteerRequirement is None:
        res.status_code = 404
        return {"detail": "Relief effort and/or volunteer requirement not found."}
    
    volunteer:Volunteer = db.query(Volunteer).filter(and_(Volunteer.volunteer_id == user.user_id, Volunteer.id == id)).first()

    if volunteer is not None:
        res.status_code = 400
        return {"detail": "Is already a volunteer."}
    
    volunteer = Volunteer()

    volunteer.volunteer_id = user.user_id
    volunteer.volunteer_requirement_id = id
    volunteer.relief_id = id
    volunteer.status = 'PENDING'

    db.add(volunteer)
    db.commit()

    volunteer = db.query(Volunteer).filter(Volunteer.volunteer_id == user.user_id).first()

    return {"details": "Successfully applied as a volunteer.",
            "volunteer_id" : volunteer.id}

@router.patch("/application/approve/{vol_request_id}")
def approveApplication (vol_request_id:int, db:DB, res:Response, user:AuthDetails = Depends(get_current_user)):
    volunteer:Volunteer = db.query(Volunteer).filter(Volunteer.id == vol_request_id).first()

    if volunteer is None:
        res.status_code = 404
        return {"detail": "Volunteer request not found."}
    
    reliefEffort = db.query(ReliefEffort).filter(ReliefEffort.id == volunteer.relief_id).first()

    authorized = True
    
    if user.level == 4:
        # admins can view this easily
        authorized == True
    elif reliefEffort.owner_type == 'USER':
        if reliefEffort.owner_id != user.user_id:
            authorized == False
    else:
        org:Organization = db.query(Organization).filter(Organization.id == reliefEffort.owner_id).first()
        if user.user_id != org.owner_id:
            authorized == False
    
    if authorized == False:
        if reliefEffort.owner_id != user.user_id:
            res.status_code = 403
            return {'detail' : 'Insufficient authorization to add volunteer requirements.'}
    
    volunteer.status = 'APPROVED'
    volunteer.updated_at = datetime.now()

    db.commit()
    #missing feature - send notification through email

    return {"detail": "Volunteer approved."}

@router.patch("/application/reject/{vol_request_id}")
def rejectApplication (vol_request_id:int, db:DB, res:Response, user:AuthDetails = Depends(get_current_user)):
    volunteer:Volunteer = db.query(Volunteer).filter(Volunteer.id == vol_request_id).first()

    if volunteer is None:
        res.status_code = 404
        return {"detail": "Volunteer request not found."}
    
    reliefEffort = db.query(ReliefEffort).filter(ReliefEffort.id == volunteer.relief_id).first()

    authorized = True
    
    if user.level == 4:
        # admins can view this easily
        authorized == True
    elif reliefEffort.owner_type == 'USER':
        if reliefEffort.owner_id != user.user_id:
            authorized == False
    else:
        org:Organization = db.query(Organization).filter(Organization.id == reliefEffort.owner_id).first()
        if user.user_id != org.owner_id:
            authorized == False
    
    if authorized == False:
        if reliefEffort.owner_id != user.user_id:
            res.status_code = 403
            return {'detail' : 'Insufficient authorization to add volunteer requirements.'}
    
    volunteer.status = 'REJECTED'
    volunteer.updated_at = datetime.now()

    db.commit()
    #missing feature - send notification through email

    return {"detail": "Volunteer rejected."}

## Temporarily commented out application removal - might not be used
# @router.delete("/{id}/remove/{user_id}")
# def removeApplication (id:int, user_id:int, db:DB, res:Response):
#     volunteerRequirement:VolunteerRequirement = db.query(VolunteerRequirement).filter(and_(VolunteerRequirement.relief_id == id, VolunteerRequirement.is_deleted == False)).first()

#     if volunteerRequirement is None:
#         res.status_code = 404
#         return {"detail": "Relief effort not found."}
    
#     volunteer:Volunteer = db.query(Volunteer).filter(Volunteer.volunteer_id == user_id).first()

#     if volunteer is None:
#         res.status_code = 404
#         return {"detail": "User not found."}
    
#     volunteer.is_deleted = True

#     db.commit()
#     #missing feature - send notification through email

#     return {"detail": "Volunteer removed."}

