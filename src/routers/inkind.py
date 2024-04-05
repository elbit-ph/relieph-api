from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, status, Response
from pydantic import BaseModel
from dependencies import get_db_session, get_logger, get_s3_handler, get_current_user
from services.db.database import Session
from services.db.models import Organization, InkindDonation, InkindDonationRequirement, ReliefEffort
from dependencies import get_db_session
from sqlalchemy import and_
from services.log.log_handler import LoggingService
from services.aws.s3_handler import S3_Handler
from models.auth_details import AuthDetails
from util.auth.auth_tool import authorize
from datetime import date, datetime

router = APIRouter(
    prefix="/inkind",
    tags=["inkind"],
    dependencies=[Depends(get_db_session), Depends(get_logger)]
)

DB = Annotated[Session, Depends(get_db_session)]
Logger = Annotated[LoggingService, Depends(get_logger)]
S3Handler = Annotated[S3_Handler, Depends(get_s3_handler)]

class InKind(BaseModel):
    name: str
    description: str
    count: int

class Pledge(BaseModel):
    requirement_id: int
    amount: int

# ===============================================

# Prototyped auth checker for foundation
# implement this for ALL routers later on
def is_user_organizer(user: AuthDetails, org_id:int, db:DB):
    org:Organization = db.query(Organization).filter(and_(Organization.id == org_id, Organization.is_active == True)).first()
    
    if org is None:
        return False

    return True

def is_authorized(owner_id:int, owner_type:str, user: AuthDetails, db:DB):
    if user.level == 4:
        return True
    match owner_type:
        case 'USER':
            if user.user_id != owner_id:
                return False
        case 'ORGANIZATION':
            if is_user_organizer(user, owner_id, db) == False:
                return False
        case _:
            return False
    return True

# ==========================================

#get the list of inkind donations
@router.get("/{relief_id}")
async def get_inkind_donations(db:DB, relief_id: int, res: Response, p: int = 1, c: int = 10, status:str = "all", user:AuthDetails = Depends(get_current_user)): 
    authorize(user, 2, 4)

    reliefEffort:ReliefEffort = db.query(ReliefEffort).filter(and_(ReliefEffort.id == relief_id, ReliefEffort.is_deleted == False)).first()

    if reliefEffort is None: 
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Relief Effort is not found."
        )

    # check authorization
    if is_authorized(reliefEffort.owner_id, reliefEffort.owner_type, user, db) == False:
        res.status_code = 403
        return {'detail' : 'Unauthorized access to inkind donation list'}

    donations:List[InkindDonation] = List[InkindDonation]

    retrieve_donation_query = and_(InkindDonation.relief_id == relief_id, InkindDonation.is_deleted == False)

    status = status.upper()
    
    if status == 'ALL':
        donations = db.query(InkindDonation).filter(retrieve_donation_query).limit(c).offset((p-1)*c).all()
    else:
        donations = db.query(InkindDonation).filter(and_(retrieve_donation_query, InkindDonation.status == status)).limit(c).offset((p-1)*c).all()

    return donations

#get specifics of an inkind donation requirement
@router.get("/requirements/{inkind_requirement_id}")
async def get_inkind_requirement(db:DB, inkind_requirement_id: int, res: Response):
    inkind:InkindDonationRequirement = db.query(InkindDonationRequirement).filter(and_(InkindDonationRequirement.id == inkind_requirement_id, InkindDonationRequirement.is_deleted == False)).first()

    if inkind is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inkind requirement not found."
        )
    
    remaining = db.query(InkindDonation).filter(and_(InkindDonation.id == inkind_requirement_id, InkindDonation.status == 'DELIVERED')).all()

    return {
        "name": inkind.name,
        "description": inkind.description,
        "count": inkind.count,
        "remaining" : len(remaining)
    }

#adds inkind donation requirement
# NOTE: temporarily disabled addition of donation requirement until notice from frontend team
# @router.post("/{relief_id}")
# async def addinkind(db:DB, relief_id:int, inkind:InKind):
#     reliefEffort:ReliefEffort = db.query(ReliefEffort).filter(and_(ReliefEffort.id == relief_id, ReliefEffort.is_deleted == False)).first()

    
#     if reliefEffort is None: 
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Relief Effort is not found."
#         )
    
#     donation = InkindDonationRequirement(name = inkind.name, description = inkind.description, count = inkind.count)
#     donation.relief_id = relief_id

#     db.add(donation)
#     db.commit()
#     db.refresh(donation)
#     db.close()

#user pledges donation

class PledgeDTO(BaseModel):
    amount: int
    expiry_date: date

@router.post("/requirements/{inkind_requirement_id}")
async def pledgedonation(db:DB, inkind_requirement_id:int, body:PledgeDTO, user: AuthDetails = Depends(get_current_user)):
    authorize(user, 1, 3)

    if body.expiry_date < date.today():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Expiration invalid. Only donate unexpired goods."
        )

    inkind_requirement:InkindDonationRequirement = db.query(InkindDonationRequirement).filter(and_(InkindDonationRequirement.id == inkind_requirement_id, InkindDonationRequirement.is_deleted == False)).first()
    
    if inkind_requirement is None: 
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Relief Effort is not found."
        )
    
    donation: InkindDonation = InkindDonation()

    donation.inkind_requirement_id = inkind_requirement.id
    donation.relief_id = inkind_requirement.relief_id
    donation.donor_id = user.user_id
    donation.quantity = body.amount
    donation.status = 'PENDING'
    donation.expiry = body.expiry_date

    db.add(donation)
    db.commit()

    # send notif to organizer

    return {'detail' : 'Successfully added pledged donation.'}

#mark as already delivered since it is an instant donation
@router.post("/{inkind_requirement_id}/instant-donation")
async def instantdonation(db:DB, inkind_requirement_id:int, body:PledgeDTO, user: AuthDetails = Depends(get_current_user)):
    authorize(user, 2, 3)
    
    if body.expiry_date < date.today():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Expiration invalid. Only donate unexpired goods."
        )
    
    inkind_requirement:InkindDonationRequirement = db.query(InkindDonationRequirement).filter(and_(InkindDonationRequirement.id == inkind_requirement_id, InkindDonationRequirement.is_deleted == False)).first()
    
    if inkind_requirement is None: 
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Relief Effort is not found."
        )
    
    donation: InkindDonation = InkindDonation()

    donation.inkind_requirement_id = inkind_requirement.id
    donation.relief_id = inkind_requirement.relief_id
    donation.donor_id = user.user_id
    donation.quantity = body.amount
    donation.status = 'DELIVERED'
    donation.expiry = body.expiry_date

    db.add(donation)
    db.commit()

    return {'detail' : 'Successfully added instant donation.'}

#mark as delivered
@router.patch("/donation/{donation_id}/delivered")
async def delivereddonation(db:DB, res: Response, donation_id:int, user: AuthDetails = Depends(get_current_user)):
    authorize(user, 2, 3)

    inkind:InkindDonation = db.query(InkindDonation).filter(and_(InkindDonation.id == donation_id, InkindDonation.is_deleted == False)).first()
    
    if inkind is None:
        raise HTTPException(
            status_code= status.HTTP_404_NOT_FOUND,
            detail="Inkind Donation not found."
        )
    
    relief_effort:ReliefEffort = db.query(ReliefEffort).filter(ReliefEffort.id == inkind.relief_id).first()

    if is_authorized(relief_effort.owner_id, relief_effort.owner_type, user, db) == False:
        res.status_code = 403
        return {'detail' : 'Unauthorized to mark donation as delivered'}
    
    inkind.status = "DELIVERED"
    inkind.updated_at = datetime.now()

    db.commit()

    # send notif to user

    return {'detail' : 'Successfully marked donation as delivered'}

#mark as cancelled
@router.patch("/donation/{donation_id}/cancelled")
async def cancel_leddonation(db:DB, res: Response, donation_id:int, user: AuthDetails = Depends(get_current_user)):
    authorize(user, 2, 4)

    inkind:InkindDonation = db.query(InkindDonation).filter(and_(InkindDonation.id == donation_id, InkindDonation.is_deleted == False)).first()
    
    if inkind is None:
        raise HTTPException(
            status_code= status.HTTP_404_NOT_FOUND,
            detail="Inkind Donation not found."
        )
    
    relief_effort:ReliefEffort = db.query(ReliefEffort).filter(ReliefEffort.id == inkind.relief_id).first()

    if is_authorized(relief_effort.owner_id, relief_effort.owner_type, user, db) == False:
        res.status_code = 403
        return {'detail' : 'Unauthorized to mark donation as delivered'}
    
    inkind.status = "CANCELLED"   
    inkind.updated_at = datetime.now()

    db.commit()

    return {'detail' : 'Successfully marked donation as cancelled'}