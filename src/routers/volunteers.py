from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, status, Response
from dependencies import get_logger, get_current_user
from services.db.database import Session, engine
from services.db.models import Volunteer, VolunteerRequirement, ReliefEffort, User
from services.email.volunteer_email_handler import VolunteerEmailHandler
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

db = Session()
volunteer_email_handler = VolunteerEmailHandler()

@router.get("/{relief_id}")
def retrieve_volunteer_requirements(relief_id:int):
    """
    Retrieve list of volunteer requirements for relief `relief_id`
    """
    # get relief effort
    reliefEffort:ReliefEffort = db.query(ReliefEffort).filter(and_(ReliefEffort.id == relief_id, ReliefEffort.is_deleted == False)).first()

    # check if relief effort exists
    if reliefEffort is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Relief effort not found."
        )
    
    volunteer_requirements:List[VolunteerRequirement] = db.query(VolunteerRequirement).filter(and_(VolunteerRequirement.relief_id == relief_id, VolunteerRequirement.is_deleted == False)).all()

    return volunteer_requirements

@router.get("/{relief_id}/volunteers")
def retrieve_applicants(relief_id:int, type:str, res:Response, user:AuthDetails = Depends(get_current_user)):
    # check for authorization
    authorize(user, 2, 4)

    relief_effort:ReliefEffort = db.query(ReliefEffort).filter(and_(ReliefEffort.id == relief_id, ReliefEffort.is_deleted == False)).first()

    if relief_effort is None:
        res.status_code = 404
        return {'detail' : 'Relief effort not found.'}
    
    # check if user is authorized to check on behalf of user
    if is_authorized(relief_effort.owner_id, relief_effort.owner_type, user) == False:
        res.status_code = 403
        return {'detail' : 'Not authorized to view volunteer list'}
    
    type = type.lower()

    if type not in ('pending', 'approved', 'rejected'):
        res.status_code = 400
        return {'detail' : 'Volunteer type not supported'}
    
    volunteers = []

    with engine.connect() as con:
        rs = con.execute(f"SELECT \
                           v.relief_id, \
                           u.username, \
                           v.status, \
                           u.created_at \
                           FROM volunteers v \
                           JOIN users u \
                           ON v.volunteer_id = u.id \
                           WHERE \
                           v.relief_id = {relief_id} \
                           AND v.status = '{type}'")
        
        for row in rs:
            volunteers.append({
                'relief_id' : row[0],
                'username' : row[1],
                'status' : row[2],
                'created_at' : row[3],
            })

    return volunteers

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

@router.post("/{volunteer_requirement_id}/apply")
def apply_as_volunteer(volunteer_requirement_id:int, res:Response, user:AuthDetails = Depends(get_current_user)):
    """
    Apply as volunteer to a relief, specifically for volunteer requirement `id`
    """
    volunteer_requirement:VolunteerRequirement = db.query(VolunteerRequirement).filter(and_(VolunteerRequirement.id == volunteer_requirement_id, VolunteerRequirement.is_deleted == False)).first()
    
    # check if volunteer requirement exists
    if volunteer_requirement is None:
        res.status_code = 404
        return {"detail": "Volunteer requirement not found."}
    
    volunteer:Volunteer = db.query(Volunteer).filter(Volunteer.volunteer_id == user.user_id).first()

    # check if volunteer already exists
    if volunteer is not None:
        res.status_code = 400
        return {"detail": "Is already a volunteer."}
    
    volunteer = Volunteer()

    volunteer.volunteer_id = user.user_id
    volunteer.volunteer_requirement_id = volunteer_requirement_id
    volunteer.relief_id = volunteer_requirement.relief_id

    db.add(volunteer)
    db.commit()

    return {"details": "Successfully applied as a volunteer."}

@router.patch("/{volunteer_requirement_id}/approve/{user_id}")
async def approve_application (volunteer_requirement_id:int, user_id:int, res:Response, user : AuthDetails = Depends(get_current_user)):
    """
    Approve volunteer application
    """

    volunteer_requirement:VolunteerRequirement = db.query(VolunteerRequirement).filter(and_(VolunteerRequirement.id == volunteer_requirement_id, VolunteerRequirement.is_deleted == False)).first()

    # check if volunteer requirement exists
    if volunteer_requirement is None:
        res.status_code = 404
        return {"detail": "Relief effort not found."}
    
    volunteer:Volunteer = db.query(Volunteer).filter(Volunteer.volunteer_id == user_id).first()

    # check if volunteer exists
    if volunteer is None:
        res.status_code = 404
        return {"detail": "User not found."}
    
    relief:ReliefEffort = db.query(ReliefEffort).filter(and_(ReliefEffort.id == volunteer_requirement.relief_id)).first()
    # check for authorization
    if is_authorized(relief.owner_id, relief.owner_type, user) == False:
        res.status_code = 403
        return {'detail' : 'Not authorized to access this resource.'}
    
    volunteer.status = 'APPROVED'

    volunteer_requirement.count += 1

    db.commit()
    
    _user:User = db.query(User).filter(and_(User.id == volunteer.volunteer_id)).first()
    await volunteer_email_handler.send_volunteer_acceptance_notice(_user.first_name, _user.email, relief.name)

    return {"detail": "Volunteer approved."}

@router.patch("/{volunteer_requirement_id}/reject/{user_id}")
async def reject_application (volunteer_requirement_id:int, user_id:int, res:Response, user:AuthDetails = Depends(get_current_user)):
    """
    Reject volunteer application
    """

    volunteerRequirement:VolunteerRequirement = db.query(VolunteerRequirement).filter(and_(VolunteerRequirement.id == volunteer_requirement_id, VolunteerRequirement.is_deleted == False)).first()

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
    
    _user:User = db.query(User).filter(and_(User.id == volunteer.volunteer_id)).first()
    await volunteer_email_handler.send_volunteer_rejection_notice(_user.first_name, _user.email, relief.name)

    return {"detail": "Volunteer rejected."}

@router.delete("/{volunteer_requirement_id}/remove/")
def remove_application (volunteer_requirement_id:int, user_id:int, res:Response, user: AuthDetails = Depends(get_current_user)):
    """
    Remove application. Used for users who want to remove their application from a volunteer event
    """
    authorize(user, 1,4)

    volunteer_requirement:VolunteerRequirement = db.query(VolunteerRequirement).filter(and_(VolunteerRequirement.id == volunteer_requirement_id, VolunteerRequirement.is_deleted == False)).first()

    # check if volunteer requirement exists
    if volunteer_requirement is None:
        res.status_code = 404
        return {"detail": "Relief effort not found."}
    
    volunteer:Volunteer = db.query(Volunteer).filter(Volunteer.volunteer_id == user.user_id).first()

    # check if volunteer exists
    if volunteer is None:
        res.status_code = 404
        return {"detail": "User not found."}
    
    # soft delete volunteer
    volunteer.is_deleted = True

    db.commit()

    return {"detail": "Volunteer removed."}

