from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, status, Response, Body, Form
from dependencies import get_logger, get_current_user, get_organization_email_handler, get_file_handler
from services.db.database import Session
from services.db.models import Organization, SponsorshipRequest, User, ReliefEffort
from services.log.log_handler import LoggingService
from services.email.organization_email_handler import OrganizationEmailHandler
from services.storage.file_handler import FileHandler
from models.auth_details import AuthDetails
from util.auth.auth_tool import authorize
from pydantic import BaseModel
from datetime import datetime
from sqlalchemy import and_

router = APIRouter(
    prefix="/foundations",
    tags=["foundations"],
    dependencies=[Depends(get_logger)]
)

# [Session, Depends(get_db_session)]
_fileHandler = Annotated[FileHandler, Depends(get_file_handler)]
Logger = Annotated[LoggingService, Depends(get_logger)]
db = Session()

# NOTE: foundations are organizations with tier level 2

@router.get("/")
async def retrieve_foundations(file_handler:_fileHandler, p: int = 1, c: int = 10):
    """
    Retrieve foundations.
    """

    # Get list of active organizations from database
    orgs: List[Organization] = db.query(Organization).filter(and_(Organization.is_active == True, Organization.tier == 2)).limit(c).offset((p-1)*c).all()

    # Initialize empty list to store retrieved data
    to_return = []

    # Extract necessary data and generate profile links for each organization
    for org in orgs:
        profile_link = await file_handler.get_org_profile(org.id)
        to_return.append({
            "id": org.id,
            "owner_id": org.owner_id,
            "name": org.name,
            "description": org.description,
            "tier": org.tier,
            "created_at": org.created_at,
            "profile_link": profile_link
        })

    return to_return

@router.get("/{id}")
async def retrieve_foundation(id:int, file_handler:_fileHandler):
    """
    Retrieve foundation with `id`
    """
    
    # Retrieve foundation from database
    foundation: Organization = db.query(Organization).filter(and_(Organization.id == id, Organization.tier == 2, Organization.is_deleted == False)).first()

    # Check if organization exists, raise 404 Not Found if not
    if foundation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found."
        )

    # Get organization profile picture link
    profile_link = await file_handler.get_org_profile(id)

    # Return organization details as a dictionary
    return {
        "id": foundation.id,
        "owner_id": foundation.owner_id,
        "name": foundation.name,
        "description": foundation.description,
        "tier": foundation.tier,
        "is_active": foundation.is_active,  # Include "is_active" field
        "created_at": foundation.created_at,
        "profile_link": profile_link
    }

# clarify if organizations can be accredited
# @router.get("/{foundation_id}/sponsored/organizations")
# def retrieve_sponsored_organizations(foundation_id:int, p: int = 1, c: int = 10):
#     """
#     Retrieve sponsored organizations of a foundation
#     """
#     sponsored_orgs :List[Organization] = db.query(Organization).filter(and_(Organization.sponsor_id == foundation_id, Organization.is_deleted == True)).limit(c).offset((p-1)*c).all()
#     return sponsored_orgs

@router.get("/{foundation_id}/sponsored/users")
def retrieve_sponsored_users(foundation_id:int, p: int = 1, c: int = 10):
    """
    Retrieve sponsored users of a foundation
    """
    sponsored_users : List[User] = db.query(User).filter(and_(User.sponsor_id == foundation_id, Organization.is_deleted == True)).limit(c).offset((p-1)*c).all()
    return sponsored_users

@router.get("/{id}/sponsored/requests")
def retrieve_sponsorship_request(id:int, res:Response, f:str = None, user: AuthDetails = Depends(get_current_user)):
    """
    Retrieve sponsorship request
    """
    authorize(user, 3,3)

    foundation:Organization = db.query(Organization).filter(and_(Organization.tier == 4, Organization.id == id)).first()

    # check if foundation exists
    if foundation is None:
        res.status_code = 404
        return {'detail' : 'Foundation not found.'}

    # check if user is authorize to act on behalf of foundation 
    if user.user_id != foundation.owner_id:
        res.status_code = 403
        return {'detail' : 'Insufficient authorization to view sponsorship requests.'}

    reqs = List[SponsorshipRequest]

    # get requests according to `f` owner type
    match f:
        case 'users':
            reqs = db.query(SponsorshipRequest).filter(and_(SponsorshipRequest.foundation_id == id, SponsorshipRequest.owner_type == 'USER', SponsorshipRequest.is_deleted == False, SponsorshipRequest.status == 'PENDING')).all()
        case 'organizations':
            reqs = db.query(SponsorshipRequest).filter(and_(SponsorshipRequest.foundation_id == id, SponsorshipRequest.owner_type == 'ORGANIZATION',SponsorshipRequest.is_deleted == False, SponsorshipRequest.status == 'PENDING')).all()
        case _:
            reqs = db.query(SponsorshipRequest).filter(and_(SponsorshipRequest.foundation_id == id, SponsorshipRequest.is_deleted == False, SponsorshipRequest.status == 'PENDING')).all()

    return reqs

class sponsorshipRequestDTO(BaseModel):
    owner_id: int
    sponsorship_request_id: int
    action: str

@router.patch("/{id}/user")
async def resolve_user_sponsorship_request(id:int, body:sponsorshipRequestDTO, res:Response, user: AuthDetails = Depends(get_current_user)):
    """
    resolves user sponsorship request. Updates user's sponsor id on success.
    """
    # check user authorization
    authorize(user, 3,3)

    sponsorship_request:SponsorshipRequest = db.query(SponsorshipRequest).filter(and_(SponsorshipRequest.status == 'PENDING', SponsorshipRequest.owner_id == user.user_id, SponsorshipRequest.owner_type == 'USER')).first()

    # check if relief effort exists
    if sponsorship_request is None:
        res.status_code = 404
        return {'detail' : 'RSponsorship request does not exists'}

    _user:User = db.query(User).filter(User.id == user.user_id).first()

    match body.action:
        case 'approve':
            user.sponsor_id = sponsorship_request.foundation_id
            _user.updated_at = datetime.now()

            sponsorship_request.status = 'APPROVED'
            sponsorship_request.updated_at = datetime.now()

            db.commit()
        case 'reject':
            sponsorship_request.status = 'REJECTED'
            sponsorship_request.updated_at = datetime.now()
            db.commit()
            return {'detail' : 'Rejected sponsorship request'}
        case _:
            res.status_code = 406
            return {'detail' : 'Invalid action.'}
    
    return {'detail': 'Successfully resolved user sponsorship request.'}