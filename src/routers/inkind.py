from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, status, Response
from pydantic import BaseModel
from dependencies import get_current_user
from services.db.database import Session
from services.db.models import Organization, InkindDonation, InkindDonationRequirement, ReliefEffort
from sqlalchemy import and_
from models.auth_details import AuthDetails
from util.auth.auth_tool import authorize, is_authorized
from datetime import date, datetime

router = APIRouter(
    prefix="/inkind",
    tags=["inkind"],
    dependencies=[]
)

db = Session()

class InKind(BaseModel):
    name: str
    description: str
    count: int

class Pledge(BaseModel):
    requirement_id: int
    amount: int

@router.get("/donations/{relief_id}")
async def get_inkind_donations(relief_id: int, res: Response, p: int = 1, c: int = 10, status:str = "all", user:AuthDetails = Depends(get_current_user)): 
    """
    Get list of inkind donations for relief `relief_id`
    """

    # check for authorization
    authorize(user, 2, 4)

    reliefEffort:ReliefEffort = db.query(ReliefEffort).filter(and_(ReliefEffort.id == relief_id, ReliefEffort.is_deleted == False)).first()

    # check if relief effort exists
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
    
    # filter base on status
    if status == 'ALL':
        donations = db.query(InkindDonation).filter(retrieve_donation_query).limit(c).offset((p-1)*c).all()
    else:
        donations = db.query(InkindDonation).filter(and_(retrieve_donation_query, InkindDonation.status == status)).limit(c).offset((p-1)*c).all()

    return donations

@router.get("/requirements/{inkind_requirement_id}")
async def get_inkind_requirement(inkind_requirement_id: int, res: Response):
    """
    get specifics of an inkind donation requirement
    """
    inkind_requirement:InkindDonationRequirement = db.query(InkindDonationRequirement).filter(and_(InkindDonationRequirement.id == inkind_requirement_id, InkindDonationRequirement.is_deleted == False)).first()

    # check if inkind requirement exists
    if inkind_requirement is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inkind requirement not found."
        )
    
    # get count of how many items of `inkind_requirement` are needed currently
    remaining = db.query(InkindDonation).filter(and_(InkindDonation.id == inkind_requirement_id, InkindDonation.status == 'DELIVERED')).all()

    return {
        "name": inkind_requirement.name,
        "description": inkind_requirement.description,
        "count": inkind_requirement.count,
        "remaining" : len(remaining)
    }

class PledgeDTO(BaseModel):
    amount: int
    expiry_date: date

@router.post("/donations/{inkind_requirement_id}")
async def pledge_donation(inkind_requirement_id:int, body:PledgeDTO, user: AuthDetails = Depends(get_current_user)):
    """
    User pledges their donation of goods.
    """

    # checks authorization
    authorize(user, 1, 3)

    # check if item expiry is valid
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

    return {'detail' : 'Successfully added pledged donation.'}

@router.post("/donations/{inkind_requirement_id}/instant")
async def create_instant_donation(inkind_requirement_id:int, body:PledgeDTO, res:Response, user: AuthDetails = Depends(get_current_user)):
    """
    Create instant donation. Marked as `DELIVERED` automatically.
    """

    # checks for user authorization
    authorize(user, 2, 3)
    
    # checks validity of expiry
    if body.expiry_date < date.today():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Expiration invalid. Only donate unexpired goods."
        )
    
    inkind_requirement:InkindDonationRequirement = db.query(InkindDonationRequirement).filter(and_(InkindDonationRequirement.id == inkind_requirement_id, InkindDonationRequirement.is_deleted == False)).first()
    
    # checks if inkind requirement exists
    if inkind_requirement is None: 
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Relief Effort is not found."
        )
    
    relief:ReliefEffort = db.query(ReliefEffort).filter(ReliefEffort.id == inkind_requirement.relief_id).first()

    if is_authorized(relief.owner_id, relief.owner_type, user) == False:
        res.status_code = 403
        return {'detail' : 'Unauthorized access to this resource.'}
    
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

@router.patch("/donations/{donation_id}/delivered")
async def mark_donation_as_delivered(res: Response, donation_id:int, user: AuthDetails = Depends(get_current_user)):
    """
    Mark pledged donation as delivered
    """

    # check for authorization
    authorize(user, 2, 3)

    inkind:InkindDonation = db.query(InkindDonation).filter(and_(InkindDonation.id == donation_id, InkindDonation.is_deleted == False)).first()
    
    # check if inkind donation was previously pledged
    if inkind is None:
        raise HTTPException(
            status_code= status.HTTP_404_NOT_FOUND,
            detail="Inkind Donation not found."
        )
    
    relief_effort:ReliefEffort = db.query(ReliefEffort).filter(ReliefEffort.id == inkind.relief_id).first()

    # check if user is authorized to mark donation as delivered
    if is_authorized(relief_effort.owner_id, relief_effort.owner_type, user) == False:
        res.status_code = 403
        return {'detail' : 'Unauthorized to mark donation as delivered'}
    
    inkind.status = "DELIVERED"
    inkind.updated_at = datetime.now()

    db.commit()

    # send notif to user

    return {'detail' : 'Successfully marked donation as delivered'}

@router.patch("/donations/{donation_id}/cancelled")
async def mark_donation_as_canceled(res: Response, donation_id:int, user: AuthDetails = Depends(get_current_user)):
    """
    Mark previously pledged donation as cancelled
    """

    # check for authorization
    authorize(user, 2, 3)

    inkind:InkindDonation = db.query(InkindDonation).filter(and_(InkindDonation.id == donation_id, InkindDonation.is_deleted == False)).first()

    # check if inkind donation was previously pledged    
    if inkind is None:
        raise HTTPException(
            status_code= status.HTTP_404_NOT_FOUND,
            detail="Inkind Donation not found."
        )
    
    relief_effort:ReliefEffort = db.query(ReliefEffort).filter(ReliefEffort.id == inkind.relief_id).first()

    # check if user is authorized to mark donation as cancelled
    if is_authorized(relief_effort.owner_id, relief_effort.owner_type, user) == False:
        res.status_code = 403
        return {'detail' : 'Unauthorized to mark donation as cancelled'}
    
    inkind.status = "CANCELLED"   
    inkind.updated_at = datetime.now()

    db.commit()

    return {'detail' : 'Successfully marked donation as cancelled'}