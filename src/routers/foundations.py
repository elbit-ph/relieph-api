from typing import Annotated, List
from fastapi import APIRouter, Depends, UploadFile, HTTPException, status, Response, Body, Form
from dependencies import get_db_session, get_logger, get_current_user, get_organization_email_handler
from services.db.database import Session
from services.db.models import Organization, User, Address, SponsorshipRequest
from services.log.log_handler import LoggingService
from services.email.organization_email_handler import OrganizationEmailHandler
from models.auth_details import AuthDetails
from util.auth.auth_tool import authorize
from pydantic import BaseModel, Json
from datetime import datetime
from sqlalchemy import and_
import json
from types import SimpleNamespace

router = APIRouter(
    prefix="/foundations",
    tags=["foundations"],
    dependencies=[Depends(get_db_session), Depends(get_logger)]
)

DB = Annotated[Session, Depends(get_db_session)]
Logger = Annotated[LoggingService, Depends(get_logger)]


# NOTE: foundations are organizations with tier level 4

@router.get("/")
def retrieveFoundations(db: DB, p: int = 1, c: int = 10):
    return db.query(Organization).filter(and_(Organization.is_active, Organization.tier == 4)).limit(c).offset((p-1)*c).all()

@router.get("/{id}")
def retrieveFoundation(db:DB, id:int):
    foundation:Organization = db.query(Organization).filter(and_(Organization.id == id, Organization.is_deleted == False, Organization.tier == 4)).first()

    if foundation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Foundation not found."
        )
    return foundation


@router.get("/{id}/sponsored")
def retrieveSponsored(db:DB, id:int):
    sponsored_orgs :List[Organization] = db.query(Organization).filter(and_(Organization.sponsor_id == id, Organization.is_deleted == True)).all()
    return sponsored_orgs
# make foundation creation as an application

@router.get("/{id}/sponsored/requests")
def retrieveSponsorshipRequest(db:DB, id:int, res:Response, user: AuthDetails = Depends(get_current_user)):
    foundation:Organization = db.query(Organization).filter(and_(Organization.tier == 4, Organization.id == id)).first()

    if foundation is None:
        res.status_code = 404
        return {'detail' : 'Foundation not found.'}

    if user.user_id != foundation.owner_id:
        res.status_code = 403
        return {'detail' : 'Insufficient authorization to view sponsorship requests.'}

    reqs:List[SponsorshipRequest] = db.query(SponsorshipRequest).filter(and_(SponsorshipRequest.foundation_id == id, SponsorshipRequest.is_deleted == False, SponsorshipRequest.status == 'PENDING')).all()

    return reqs

class sponsorshipRequestDTO(BaseModel):
    owner_id: int
    sponsorship_request_id: int
    action: str

@router.patch("/{id}")
def resolveSponsorshipRequest(db: DB, id:int, body:sponsorshipRequestDTO, res:Response, user: AuthDetails = Depends(get_current_user)):
    authorize(user,3,5)
    foundation:Organization = db.query(Organization).filter(and_(Organization.id == id, Organization.tier == 4, Organization.is_deleted == False)).first()
    org: Organization = db.query(Organization).filter(and_(Organization.id == body.owner_id, Organization.is_deleted == False)).first()
    sponsorship_request = db.query(SponsorshipRequest).filter(and_(SponsorshipRequest.id == body.sponsorship_request_id)).first()

    if sponsorship_request is None:
        res.status_code = 404
        return {'detail' : 'Sponsorship request not found.'}

    # check if user is authorized to act on behalf of foundation
    # depends on owner type
    if foundation.owner_id != user.user_id:
        res.status_code = 403
        return {'detail' : 'Insufficient authorization to act behalf of foundation.'}

    # check if action is valid (either approve or reject)
    if body.action not in ('approve', 'reject'):
        res.status_code = 406
        return {'detail' : 'Invalid action.'}

    if body.action == 'approve':
        org.sponsor_id = id
        org.updated_at = datetime.now()
        sponsorship_request.status = 'APPROVED'
    else:
        sponsorship_request.status = 'REJECTED'
    sponsorship_request.updated_at = datetime.now()

    db.commit()
    # send email notification here.

    org_owner:User = db.query(User).filter(org.owner_id == User.id).first()


    return {'detail' : f'Organization sponsorship has been successfully {body.action}.'}