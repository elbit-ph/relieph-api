from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from dependencies import get_db_session, get_logger, get_s3_handler, get_current_user
from services.db.database import Session
from services.db.models import InkindDonation, InkindDonationRequirement, ReliefEffort
from dependencies import get_db_session
from sqlalchemy import and_
from services.log.log_handler import LoggingService
from services.aws.s3_handler import S3_Handler
from models.auth_details import AuthDetails


router = APIRouter(
    prefix="/inkinddonation",
    tags=["inkinddonation"],
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

#get the list of inkind donations
@router.get("/{relief_id}")
async def getinkinddonation(db:DB, relief_id: int): 
    reliefEffort:ReliefEffort = db.query(ReliefEffort).filter(and_(ReliefEffort.id == relief_id, ReliefEffort.is_deleted == False)).first()

    if reliefEffort is None: 
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Relief Effort is not found."
        )

    donations:List[InkindDonation] = List[InkindDonation]
    donations = db.query(InkindDonation).filter(InkindDonation.relief_id == relief_id).all()

    return donations

#get specifics of an inkind donation requirement
@router.get("/inkind/{inkind_requirement_id}")
async def getinkindrequirement(db:DB, inkind_requirement_id: int):
    inkind:InkindDonationRequirement = db.query(InkindDonationRequirement).filter(and_(InkindDonationRequirement.id == inkind_requirement_id, InkindDonationRequirement.is_deleted == False)).first()

    if inkind is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inkind requirement not found."
        )

    return {
        "name": inkind.name,
        "description": inkind.description,
        "count": inkind.count
    }

#adds inkind donation requirement
@router.post("/{relief_id}")
async def addinkind(db:DB, relief_id:int, inkind:InKind):
    reliefEffort:ReliefEffort = db.query(ReliefEffort).filter(and_(ReliefEffort.id == relief_id, ReliefEffort.is_deleted == False)).first()

    
    if reliefEffort is None: 
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Relief Effort is not found."
        )
    
    donation = InkindDonationRequirement(name = inkind.name, description = inkind.description, count = inkind.count)
    donation.relief_id = relief_id

    db.add(donation)
    db.commit()
    db.refresh(donation)
    db.close()

#user pledges donation
@router.post("/{relief_id}/donation")
async def pledgedonation(db:DB, relief_id:int, pledge:Pledge, user: AuthDetails = Depends(get_current_user)):
    reliefEffort:ReliefEffort = db.query(ReliefEffort).filter(and_(ReliefEffort.id == relief_id, ReliefEffort.is_deleted == False)).first()

    
    if reliefEffort is None: 
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Relief Effort is not found."
        )
     
    pledge = InkindDonation(inkind_requirement_id = pledge.requirement_id, quantity = pledge.amount)
    pledge.relief_id = relief_id
    pledge.donor_id = user.user_id

    db.add(pledge)
    db.commit()
    db.refresh(pledge)
    db.close()

#mark as already delivered since it is an instant donation
@router.post("/{relief_id}/instant-donation")
async def instantdonation(db:DB, relief_id:int, user: AuthDetails = Depends(get_current_user)):
    reliefEffort:ReliefEffort = db.query(ReliefEffort).filter(and_(ReliefEffort.id == relief_id, ReliefEffort.is_deleted == False)).first()

    if reliefEffort is None: 
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Relief Effort is not found."
        )
    
    inkind = InkindDonation()
    inkind.relief_id = relief_id
    inkind.donor_id = user.user_id
    inkind.status = 'ALREADY DELIVERED'


    db.commit()
    db.close()

#mark as delivered
@router.patch("donation/{id}/delivered")
async def delivereddonation(db:DB, id:int):
    inkind:InkindDonation = db.query(InkindDonation).filter(and_(InkindDonation.id == id, InkindDonation.is_deleted == False)).first()
    
    if inkind is None:
        raise HTTPException(
            status_code= status.HTTP_404_NOT_FOUND,
            detail="Inkind Donation not found."
        )
    
    inkind.status = "DELIVERED"
    db.commit()
    db.close()

#mark as cancelled
@router.patch("donation/{id}/cancelled")
async def cancelleddonation(db:DB, id:int):
    inkind:InkindDonation = db.query(InkindDonation).filter(and_(InkindDonation.id == id, InkindDonation.is_deleted == False)).first()
    
    if inkind is None:
        raise HTTPException(
            status_code= status.HTTP_404_NOT_FOUND,
            detail="Inkind Donation not found."
        )
    
    inkind.status = "CANCELLED"   
    
    db.commit()
    db.close()

