from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status, Response
from dependencies import get_logger, get_current_user
from services.db.database import Session
from services.db.models import Volunteer, VolunteerRequirement, ReliefEffort
from services.log.log_handler import LoggingService
from models.auth_details import AuthDetails
from util.auth.auth_tool import authorize, is_authorized
from sqlalchemy import and_
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(
    prefix="/volunteers",
    tags=["volunteers"],
    dependencies=[Depends(get_logger)]
)

Logger = Annotated[LoggingService, Depends(get_logger)]
db = Session()

@router.get("/{id}")
def retrieve_volunteers(id:int, p: int = 1, c: int = 10):
    """
    Retrieve list of volunteers for relief `id`
    """
    # get relief effort
    reliefEffort:ReliefEffort = db.query(ReliefEffort).filter(and_(ReliefEffort.id == id, ReliefEffort.is_deleted == False)).first()

    # check if relief effort exists
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

# temporarily disable this until notice from frontend team
# @router.post("/{id}")
# def create_volunteer_requirements(body:VolunteerRequirementsDTO, res:Response, id: int):
#     """
#     Create volunteer requirements
#     """

#     volunteerRequirement:VolunteerRequirement = db.query(VolunteerRequirement).filter(and_(VolunteerRequirement.name == body.name, VolunteerRequirement.is_deleted == False)).first()

#     # check if volunteer requirement exists already
#     if volunteerRequirement is not None:
#         res.status_code = 400
#         return {"detail": "Name already exists"}
    
#     volunteerRequirement = VolunteerRequirement()

#     volunteerRequirement.relief_id = id
#     volunteerRequirement.name = body.name
#     volunteerRequirement.description = body.description
#     volunteerRequirement.count = body.count
#     volunteerRequirement.duration_days = body.duration_days

#     db.add(volunteerRequirement)
#     db.commit()

#     return {"details": "Organization created."}

@router.patch("/{id}")
def edit_volunteer_requirements(body:VolunteerRequirementsDTO, res:Response, id: int, user:AuthDetails = Depends(get_current_user)):
    """
    Edit volunteer requirement with `id`
    """

    volunteerRequirement:VolunteerRequirement = db.query(VolunteerRequirement).filter(and_(VolunteerRequirement.id == id, VolunteerRequirement.is_deleted == False)).first()

    # check if volunteer requirement exists
    if volunteerRequirement is None:
        res.status_code = 404
        return {"detail": "Volunteer requirements non-existent"}
    
    # check for authorization
    relief:ReliefEffort = db.query(ReliefEffort).filter(and_(ReliefEffort.id == volunteerRequirement.relief_id)).first()

    if is_authorized(relief.owner_id, relief.owner_type, user) == False:
        res.status_code = 403
        return {'detail' : 'Not authorized to access this resource.'}
    
    volunteerRequirement.name = volunteerRequirement.name if body.name == "" else body.name
    volunteerRequirement.description = volunteerRequirement.ndescriptioname if body.description == "" else body.description
    volunteerRequirement.count = volunteerRequirement.count if body.count == "" else body.count
    volunteerRequirement.duration_days = volunteerRequirement.duration_days if body.duration_days == "" else body.duration_days
    volunteerRequirement.updated_at = datetime.now()

    db.commit()

    return {"detail": "Volunteer requirements successfully updated."}

@router.post("/{id}/apply")
def apply_as_volunteer(id:int, res:Response, user:AuthDetails = Depends(get_current_user)):
    """
    Apply as volunteer to a relief, specifically for volunteer requirement `id`
    """
    volunteerRequirement:VolunteerRequirement = db.query(VolunteerRequirement).filter(and_(VolunteerRequirement.relief_id == id, VolunteerRequirement.is_deleted == False)).first()
    
    # check if volunteer requirement exists
    if volunteerRequirement is None:
        res.status_code = 404
        return {"detail": "Volunteer requirement not found."}
    
    volunteer:Volunteer = db.query(Volunteer).filter(Volunteer.volunteer_id == user.user_id).first()

    # check if volunteer already exists
    if volunteer is not None:
        res.status_code = 400
        return {"detail": "Is already a volunteer."}
    
    volunteer = Volunteer()

    volunteer.volunteer_id = user.user_id
    volunteer.volunteer_requirement_id = volunteerRequirement.id
    volunteer.relief_id = id

    db.add(volunteer)
    db.commit()

    return {"details": "Successfully applied as a volunteer."}

@router.patch("/{id}/approve/{user_id}")
def approve_application (id:int, user_id:int, res:Response, user : AuthDetails = Depends(get_current_user)):
    """
    Approve volunteer application
    """

    volunteerRequirement:VolunteerRequirement = db.query(VolunteerRequirement).filter(and_(VolunteerRequirement.relief_id == id, VolunteerRequirement.is_deleted == False)).first()

    # check if volunteer requirement exists
    if volunteerRequirement is None:
        res.status_code = 404
        return {"detail": "Relief effort not found."}
    
    volunteer:Volunteer = db.query(Volunteer).filter(Volunteer.volunteer_id == user_id).first()

    # check if volunteer exists
    if volunteer is None:
        res.status_code = 404
        return {"detail": "User not found."}
    
    relief:ReliefEffort = db.query(ReliefEffort).filter(and_(ReliefEffort.id == volunteerRequirement.relief_id)).first()
    # check for authorization
    if is_authorized(relief.owner_id, relief.owner_type, user) == False:
        res.status_code = 403
        return {'detail' : 'Not authorized to access this resource.'}
    
    volunteer.status = 'APPROVED'

    db.commit()
    #missing feature - send notification through email

    return {"detail": "Volunteer approved."}

@router.patch("/{id}/reject/{user_id}")
def reject_application (id:int, user_id:int, res:Response):
    """
    Reject volunteer application
    """

    volunteerRequirement:VolunteerRequirement = db.query(VolunteerRequirement).filter(and_(VolunteerRequirement.relief_id == id, VolunteerRequirement.is_deleted == False)).first()

    # check if volunteer requirement exists
    if volunteerRequirement is None:
        res.status_code = 404
        return {"detail": "Relief effort not found."}
    
    volunteer:Volunteer = db.query(Volunteer).filter(Volunteer.volunteer_id == user_id).first()
    
    # check if volunteer exists
    if volunteer is None:
        res.status_code = 404
        return {"detail": "User not found."}
    
    # check authorization
    relief:ReliefEffort = db.query(ReliefEffort).filter(and_(ReliefEffort.id == volunteerRequirement.relief_id)).first()
    # check for authorization
    if is_authorized(relief.owner_id, relief.owner_type, user) == False:
        res.status_code = 403
        return {'detail' : 'Not authorized to access this resource.'}

    volunteer.status = 'REJECTED'

    db.commit()
    
    #missing feature - send notification through email

    return {"detail": "Volunteer rejected."}

@router.delete("/{id}/remove/{user_id}")
def remove_application (id:int, user_id:int, res:Response, user: AuthDetails = Depends(get_current_user)):
    """
    Remove application
    """
    authorize(user, 1,4)

    # implement authorization here

    volunteerRequirement:VolunteerRequirement = db.query(VolunteerRequirement).filter(and_(VolunteerRequirement.relief_id == id, VolunteerRequirement.is_deleted == False)).first()

    # check if volunteer requirement exists
    if volunteerRequirement is None:
        res.status_code = 404
        return {"detail": "Relief effort not found."}
    
    volunteer:Volunteer = db.query(Volunteer).filter(Volunteer.volunteer_id == user_id).first()

    # check if volunteer exists
    if volunteer is None:
        res.status_code = 404
        return {"detail": "User not found."}
    
    if volunteer.volunteer_id != user.user_id:
        res.status_code = 403
        return {'detail' : 'Unauthorized to remove application'}
    
    # soft delete volunteer
    volunteer.is_deleted = True

    db.commit()

    return {"detail": "Volunteer removed."}

