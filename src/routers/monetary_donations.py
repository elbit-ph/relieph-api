from typing import Annotated, List
from fastapi import APIRouter, Depends, UploadFile, HTTPException, status, Response, Body
from dependencies import get_db_session, get_logger, get_s3_handler, get_current_user
from services.db.database import Session
from services.db.models import ReliefEffort, User, Address, Organization, ReceivedMoney, UsedMoney
from services.log.log_handler import LoggingService
from services.aws.s3_handler import S3_Handler
from models.auth_details import AuthDetails
from util.auth.auth_tool import authorize
from sqlalchemy import and_
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(
    prefix="/monetary-donations",
    tags=["monetary-donations"],
    dependencies=[Depends(get_db_session), Depends(get_logger)]
)

DB = Annotated[Session, Depends(get_db_session)]
Logger = Annotated[LoggingService, Depends(get_logger)]
S3Handler = Annotated[S3_Handler, Depends(get_s3_handler)]

class RecievedMoneyDTO(BaseModel):
       amount: float
       platform: str
       reference_no: str

@router.post("/{relief_id}/offline_payment")
def markOfflinePayment(relief_id:int, res:Response, db:DB, body:RecievedMoneyDTO, user:AuthDetails = Depends(get_current_user)):
       reliefEffort:ReliefEffort = db.query(ReliefEffort).filter(and_(ReliefEffort.id == relief_id, ReliefEffort.is_deleted == False)).first()

       #checks if relief effort exists in database
       if reliefEffort is None:
              raise HTTPException(
                     status_code=status.HTTP_404_NOT_FOUND,
                     detail="Relief effort not found."
              )
       
       receivedMoney:ReceivedMoney = db.query(ReceivedMoney).filter(and_(ReceivedMoney.reference_no == body.reference_no, ReceivedMoney.is_deleted == False)).first()

       #checks if donation exists in database
       if receivedMoney is not None:
              res.status_code = 400
              return {"detail": "Donation already exists."}
       
       receivedMoney = ReceivedMoney()

       receivedMoney.donor_id = user.user_id
       receivedMoney.relief_id = relief_id
       receivedMoney.amount = body.amount
       receivedMoney.platform = body.platform
       receivedMoney.reference_no = body.reference_no

       db.add(receivedMoney)
       db.commit()

       receivedMoney = db.query(ReceivedMoney).filter(and_(ReceivedMoney.reference_no == body.reference_no, ReceivedMoney.is_deleted == False)).first()

       return {"details": "Donation created.",
              "received_money_id": receivedMoney.id}
       
@router.get("/{relief_id}")
def getDonations(relief_id:int, res:Response, db:DB):
       reliefEffort:ReliefEffort = db.query(ReliefEffort).filter(and_(ReliefEffort.id == relief_id, ReliefEffort.is_deleted == False)).first()

       #checks if relief effort exists in database
       if reliefEffort is None:
              raise HTTPException(
                     status_code=status.HTTP_404_NOT_FOUND,
                     detail="Relief effort not found."
              )

       donations:ReceivedMoney = db.query(ReceivedMoney).filter(and_(ReceivedMoney.relief_id == relief_id, ReceivedMoney.is_deleted == False)).all()
       return donations

@router.get("/{monetary_donation_id}")
def getMonetaryDetails(monetary_donation_id:int, res:Response, db:DB):
       receivedMoney:ReceivedMoney = db.query(ReceivedMoney).filter(and_(ReceivedMoney.id == monetary_donation_id, ReceivedMoney.is_deleted == False)).first()
       
       #checks if monetary donation is in database
       if receivedMoney is None:
              res.status_code = 404
              return {"detail": "Monetary donation not found."}
       
       return receivedMoney       

@router.get("/{relief_id}/expenses")
def getExpenseRecords (relief_id:int, res:Response, db:DB):
       reliefEffort:ReliefEffort = db.query(ReliefEffort).filter(and_(ReliefEffort.id == relief_id, ReliefEffort.is_deleted == False)).first()

       #checks if relief effort exists in database
       if reliefEffort is None:
              raise HTTPException(
                     status_code=status.HTTP_404_NOT_FOUND,
                     detail="Relief effort not found."
              )
       
       usedMoney:UsedMoney = db.query(UsedMoney).filter(and_(UsedMoney.relief_id == relief_id, UsedMoney.is_deleted == False)).all()

       #checks if list of expenses exist in database
       if usedMoney is None:
              res.status_code = 404
              return {"detail": "Expense records non-existent."}
       
       return usedMoney

@router.get("/{relief_id}/expenses/{expense_id}")
def getExpenseRecord (relief_id:int, expense_id:int, res:Response, db:DB):
       reliefEffort:ReliefEffort = db.query(ReliefEffort).filter(and_(ReliefEffort.id == relief_id, ReliefEffort.is_deleted == False)).first()

       #checks if relief effort exists in database
       if reliefEffort is None:
              raise HTTPException(
                     status_code=status.HTTP_404_NOT_FOUND,
                     detail="Relief effort not found."
              )
       
       usedMoney:UsedMoney = db.query(UsedMoney).filter(and_(UsedMoney.relief_id == relief_id, UsedMoney.is_deleted == False, UsedMoney.id == expense_id)).first()

       #checks if list of expenses exist in database
       if usedMoney is None:
              res.status_code = 404
              return {"detail": "Expense record non-existent."}
       
       return usedMoney

class UsedMoneyDTO(BaseModel):
       amount: float
       description: str
       purchase_type: str
       reference_no: str

@router.post("/{relief_id}/expenses")
def createExpenseRecord (relief_id:int, res:Response, db:DB, body:UsedMoneyDTO):
       reliefEffort:ReliefEffort = db.query(ReliefEffort).filter(and_(ReliefEffort.id == relief_id, ReliefEffort.is_deleted == False)).first()

       #checks if relief effort exists in database
       if reliefEffort is None:
              raise HTTPException(
                     status_code=status.HTTP_404_NOT_FOUND,
                     detail="Relief effort not found."
              )
       
       usedMoney:UsedMoney = db.query(UsedMoney).filter(and_(UsedMoney.reference_no == body.reference_no, UsedMoney.is_deleted == False)).first()

       #checks if expense record is in database already
       if usedMoney is not None:
              res.status_code = 400
              return {"detail": "Expense record already exists."}
       
       #adds new expense record to database
       usedMoney = UsedMoney()

       usedMoney.relief_id = relief_id
       usedMoney.amount = body.amount
       usedMoney.description = body.description
       usedMoney.purchase_type = body.purchase_type
       usedMoney.reference_no = body.reference_no

       db.add(usedMoney)
       db.commit

       usedMoney = db.query(UsedMoney).filter(UsedMoney.reference_no == body.reference_no, UsedMoney.is_deleted == False).first()

       return {"details": "Expense record created.",
              "used_money_id": usedMoney.id}
       
       