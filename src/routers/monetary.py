from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status, Response, Body
from dependencies import get_db_session, get_logger, get_current_user
from services.db.database import Session
from services.db.models import ReliefEffort, Organization, ReceivedMoney, UsedMoney
from services.log.log_handler import LoggingService
from models.auth_details import AuthDetails
from util.auth.auth_tool import authorize
from sqlalchemy import and_
from pydantic import BaseModel

router = APIRouter(
    prefix="/monetary",
    tags=["monetary"],
    dependencies=[Depends(get_db_session), Depends(get_logger)]
)

DB = Annotated[Session, Depends(get_db_session)]
Logger = Annotated[LoggingService, Depends(get_logger)]

# ==========================

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

# ==========================

class RecievedMoneyDTO(BaseModel):
       amount: float
       platform: str
       reference_no: str

@router.post("/{relief_id}/offline_payment")
def mark_offline_payment(relief_id:int, res:Response, db:DB, body:RecievedMoneyDTO, user:AuthDetails = Depends(get_current_user)):
       authorize(user, 2, 4)

       relief_effort:ReliefEffort = db.query(ReliefEffort).filter(and_(ReliefEffort.id == relief_id, ReliefEffort.is_deleted == False)).first()

       #checks if relief effort exists in database
       if relief_effort is None:
              raise HTTPException(
                     status_code=status.HTTP_404_NOT_FOUND,
                     detail="Relief effort not found."
              )
       
       if is_authorized(relief_effort.owner_id, relief_effort.owner_type, user, db) == False:
              raise HTTPException(
                     status_code=status.HTTP_403_FORBIDDEN,
                     detail="Forbidden access to relief effort."
              )

       received_money:ReceivedMoney = db.query(ReceivedMoney).filter(and_(ReceivedMoney.reference_no == body.reference_no, ReceivedMoney.is_deleted == False)).first()

       #checks if donation exists in database
       if received_money is not None:
              res.status_code = 400
              return {"detail": "Donation already exists."}

       received_money = ReceivedMoney()

       received_money.donor_id = user.user_id
       received_money.relief_id = relief_id
       received_money.amount = body.amount
       received_money.platform = body.platform
       received_money.reference_no = body.reference_no

       db.add(received_money)

       db.commit()

       return {"details": "Donation created.",
              "received_money_id": received_money.id}

@router.get("/{relief_id}/donations")
def get_donations(relief_id:int, res:Response, db:DB, p: int = 1, c: int = 10, user:AuthDetails = Depends(get_current_user)):
       authorize(user, 2, 4)

       relief_effort:ReliefEffort = db.query(ReliefEffort).filter(and_(ReliefEffort.id == relief_id, ReliefEffort.is_deleted == False)).first()
       
       #checks if relief effort exists in database
       if relief_effort is None:
              raise HTTPException(
                     status_code=status.HTTP_404_NOT_FOUND,
                     detail="Relief effort not found."
              )
       
       if is_authorized(relief_effort.owner_id, relief_effort.owner_type, user) == False:
              raise HTTPException(
                     status_code=status.HTTP_403_FORBIDDEN,
                     detail="Unauthorized to view donations."
              )
       
       donations:ReceivedMoney = db.query(ReceivedMoney).filter(and_(ReceivedMoney.relief_id == relief_id, ReceivedMoney.is_deleted == False)).limit(c).offset((p-1)*c).all()

       return donations

@router.get("/{relief_id}/donations/{monetary_donation_id}")
def get_monetary_details(relief_id:int, monetary_donation_id:int, res:Response, db:DB, user:AuthDetails = Depends(get_current_user)):
       authorize(user, 2, 4)

       relief_effort:ReliefEffort = db.query(ReliefEffort).filter(and_(ReliefEffort.id == relief_id, ReliefEffort.is_deleted == False)).first()
       
       #checks if relief effort exists in database
       if relief_effort is None:
              raise HTTPException(
                     status_code=status.HTTP_404_NOT_FOUND,
                     detail="Relief effort not found."
              )
       
       if is_authorized(relief_effort.owner_id, relief_effort.owner_type, user) == False:
              raise HTTPException(
                     status_code=status.HTTP_403_FORBIDDEN,
                     detail="Unauthorized to view donations."
              )
       
       # only admin and / or authorized users can access this
       received_money:ReceivedMoney = db.query(ReceivedMoney).filter(and_(ReceivedMoney.id == monetary_donation_id, ReceivedMoney.is_deleted == False)).first()

       #checks if monetary donation is in database
       if received_money is None:
              res.status_code = 404
              return {"detail": "Monetary donation not found."}

       return received_money       

@router.get("/{relief_id}/expenses")
def get_expense_records (relief_id:int, res:Response, db:DB, p: int = 1, c: int = 10, user:AuthDetails = Depends(get_current_user)):
       # check authorization
       authorize(user, 2, 4)

       relief_effort:ReliefEffort = db.query(ReliefEffort).filter(and_(ReliefEffort.id == relief_id, ReliefEffort.is_deleted == False)).first()
       
       #checks if relief effort exists in database
       if relief_effort is None:
              raise HTTPException(
                     status_code=status.HTTP_404_NOT_FOUND,
                     detail="Relief effort not found."
              )
       
       if is_authorized(relief_effort.owner_id, relief_effort.owner_type, user) == False:
              raise HTTPException(
                     status_code=status.HTTP_403_FORBIDDEN,
                     detail="Unauthorized to view donations."
              )

       used_money:UsedMoney = db.query(UsedMoney).filter(and_(UsedMoney.relief_id == relief_id, UsedMoney.is_deleted == False)).limit(c).offset((p-1)*c).all()

       return used_money

@router.get("/{relief_id}/expenses/{expense_id}")
def get_expense_record (relief_id:int, expense_id:int, res:Response, db:DB, user:AuthDetails = Depends(get_current_user)):
       # check authorization
       authorize(user, 2, 4)

       relief_effort:ReliefEffort = db.query(ReliefEffort).filter(and_(ReliefEffort.id == relief_id, ReliefEffort.is_deleted == False)).first()
       
       #checks if relief effort exists in database
       if relief_effort is None:
              raise HTTPException(
                     status_code=status.HTTP_404_NOT_FOUND,
                     detail="Relief effort not found."
              )
       
       if is_authorized(relief_effort.owner_id, relief_effort.owner_type, user) == False:
              raise HTTPException(
                     status_code=status.HTTP_403_FORBIDDEN,
                     detail="Unauthorized to view donations."
              )

       expense:UsedMoney = db.query(UsedMoney).filter(and_(UsedMoney.relief_id == relief_id, UsedMoney.is_deleted == False, UsedMoney.id == expense_id)).first()

       #checks if list of expenses exist in database
       if expense is None:
              res.status_code = 404
              return {"detail": "Expense record non-existent."}

       return expense

class UsedMoneyDTO(BaseModel):
       amount: float
       description: str
       purchase_type: str
       reference_no: str

@router.post("/{relief_id}/expenses")
def create_expense_record (relief_id:int, res:Response, db:DB, body:UsedMoneyDTO, user:AuthDetails = Depends(get_current_user)):
       relief_effort:ReliefEffort = db.query(ReliefEffort).filter(and_(ReliefEffort.id == relief_id, ReliefEffort.is_deleted == False)).first()

       #checks if relief effort exists in database
       if relief_effort is None:
              raise HTTPException(
                     status_code=status.HTTP_404_NOT_FOUND,
                     detail="Relief effort not found."
              )

       # check if user is authorized to act on behalf of relief
       if is_authorized(relief_effort.owner_id, relief_effort.owner_type, user) == False:
              raise HTTPException(
                     status_code=status.HTTP_403_FORBIDDEN,
                     detail="Forbidden action."
              )

       used_money:UsedMoney = db.query(UsedMoney).filter(and_(UsedMoney.reference_no == body.reference_no, UsedMoney.is_deleted == False)).first()

       #checks if expense record is in database already
       if used_money is not None:
              res.status_code = 400
              return {"detail": "Expense record already exists."}

       #adds new expense record to database
       used_money = UsedMoney()

       used_money.relief_id = relief_id
       used_money.amount = body.amount
       used_money.description = body.description
       used_money.purchase_type = body.purchase_type
       used_money.reference_no = body.reference_no

       db.add(used_money)
       
       db.commit

       return {"details": "Expense record created.",
              "used_money_id": used_money.id}


