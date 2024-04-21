from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response, Body
from dependencies import get_current_user
from services.db.database import Session
from services.db.models import ReliefEffort, Organization, ReceivedMoney, UsedMoney, ReliefPaymentKey, User
from services.payment.payment_handler import PaymentHandler;
from models.auth_details import AuthDetails
from util.auth.auth_tool import authorize, is_authorized, is_user_organizer
from sqlalchemy import and_
from pydantic import BaseModel
import os
from dotenv import load_dotenv
from base64 import urlsafe_b64encode

load_dotenv()

router = APIRouter(
    prefix="/monetary",
    tags=["monetary"]
)

db = Session()
payment_handler = PaymentHandler(os.environ.get("ENCRYPTION"))

class RecievedMoneyDTO(BaseModel):
       amount: float
       platform: str
       reference_no: str

@router.post("/{relief_id}/offline_payment")
def mark_offline_payment(relief_id:int, res:Response, body:RecievedMoneyDTO, user:AuthDetails = Depends(get_current_user)):
       """
       Mark payment as offline transaction
       """

       # checks user authorization
       authorize(user, 2, 4)

       relief_effort:ReliefEffort = db.query(ReliefEffort).filter(and_(ReliefEffort.id == relief_id, ReliefEffort.is_deleted == False)).first()

       # checks if relief effort exists in database
       if relief_effort is None:
              raise HTTPException(
                     status_code=status.HTTP_404_NOT_FOUND,
                     detail="Relief effort not found."
              )
       
       # check if user is authorized
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

       return {"details": "Offline payment created"}

@router.get("/{relief_id}/donations")
def get_donations(relief_id:int, res:Response, p: int = 1, c: int = 10, user:AuthDetails = Depends(get_current_user)):
       """
       Retrieve donations from relief `relief_id`
       """

       # check user authorization
       authorize(user, 2, 4)

       relief_effort:ReliefEffort = db.query(ReliefEffort).filter(and_(ReliefEffort.id == relief_id, ReliefEffort.is_deleted == False)).first()
       
       # checks if relief effort exists in database
       if relief_effort is None:
              raise HTTPException(
                     status_code=status.HTTP_404_NOT_FOUND,
                     detail="Relief effort not found."
              )
       
       # check user authorization
       if is_authorized(relief_effort.owner_id, relief_effort.owner_type, user) == False:
              raise HTTPException(
                     status_code=status.HTTP_403_FORBIDDEN,
                     detail="Unauthorized to view donations."
              )
       
       donations:ReceivedMoney = db.query(ReceivedMoney).filter(and_(ReceivedMoney.relief_id == relief_id, ReceivedMoney.is_deleted == False)).limit(c).offset((p-1)*c).all()

       return donations

@router.get("/{relief_id}/donations/{monetary_donation_id}")
def get_monetary_details(relief_id:int, monetary_donation_id:int, res:Response, user:AuthDetails = Depends(get_current_user)):
       """
       Retrieve monetary donation details
       """

       # check authorization
       authorize(user, 2, 4)

       relief_effort:ReliefEffort = db.query(ReliefEffort).filter(and_(ReliefEffort.id == relief_id, ReliefEffort.is_deleted == False)).first()
       
       # checks if relief effort exists in database
       if relief_effort is None:
              raise HTTPException(
                     status_code=status.HTTP_404_NOT_FOUND,
                     detail="Relief effort not found."
              )
       
       # check if user is authorized
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
def get_expense_records (relief_id:int, res:Response, p: int = 1, c: int = 10, user:AuthDetails = Depends(get_current_user)):
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
def get_expense_record (relief_id:int, expense_id:int, res:Response, user:AuthDetails = Depends(get_current_user)):
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
def create_expense_record (relief_id:int, res:Response, body:UsedMoneyDTO, user:AuthDetails = Depends(get_current_user)):
       """
       Create expense record
       """
       relief_effort:ReliefEffort = db.query(ReliefEffort).filter(and_(ReliefEffort.id == relief_id, ReliefEffort.is_deleted == False)).first()

       # checks if relief effort exists in database
       if relief_effort is None:
              raise HTTPException(
                     status_code=status.HTTP_404_NOT_FOUND,
                     detail="Relief effort not found."
              )

       # check if user is authorized to act on behalf of relief
       if is_authorized(relief_effort.owner_id, relief_effort.owner_type, user, db) == False:
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

       return {"detail": "Expense record created."}

class MayaKeyDTO(BaseModel):
      pkey:str
      skey:str

@router.post("/register/maya/{owner_type}/{owner_id}")
async def register_maya_receiver(owner_type:str, owner_id:int, body:MayaKeyDTO, res:Response, user:AuthDetails = Depends(get_current_user)):
       """
       Register Maya Account keys for automated payment records
       """

       # checks for user authorization
       authorize(user, 2, 4)

       # check if user is allowed to access function
       if is_authorized(owner_id, owner_type, user, db) == False:
             return {'detail': 'User not authorized for action.'}
       
       resu = await payment_handler.save_maya_api_key(owner_id, owner_type, body.pkey, body.skey)
       
       # check if registration is successful
       if resu[1] == False:
              res.status_code = 400
              return {'detail' : 'Existing API Key for account.'}
      
       return {'detail' : 'Successfully saved a maya receiver'}

@router.post("/maya")
async def create_maya_checkout(relief_id:int, amount:float, res:Response):
       """
       Create instance of Maya checkout depending on relief `relief id`.
       """

       resu = await payment_handler.create_payment_session(relief_id, amount)

       # check if Maya Checkout generation is successful
       if resu[1] == False:
             match resu[0]:
                     case "ReliefEffortNonexistent":
                            res.status_code = 404
                            return {'detail': 'Relief effort non existent'}
                     case _:
                            res.status_code = 500
                            return {'detail' : 'Server-side error'}
       
       # resu contains checkoutId and redirectUrl
       return resu[0]['redirectUrl']

@router.get("/maya/redirect")
async def record_payment(status:str, rrn:str, relief_id:int, req:Request, res:Response, donor_id:int = 0):
       """
       Record payment from Maya. Accessed by Maya redirect/webhook.
       """
       
       # add condition that this endpoint only accepts traffic from Maya

       relief:ReliefEffort = db_handler.query(ReliefEffort).filter(and_(ReliefEffort.id == relief_id, ReliefEffort.is_active == True)).first()

       # check if relief effort is non-existent
       if relief is None:
             return {'detail' : 'Non-existent relief effort.'}
       
       user:User = db_handler.query(User).filter(and_(User.id == donor_id, User.is_deleted == False)).first()

       # check if user is non-existent
       if user is None:
             # mark as anonymous donation
             donor_id = 0
       
       # process payment status depending on status
       match status:
             case 'success':
                   # continue
                   res.status_code = 200
             case 'failure':
                   res.status_code = 400
                   return {'detail' : 'Payment was unsuccessful.'}
             case 'cancel':
                   res.status_code = 400
                   return {'detail' : 'Payment was cancelled'}
             case _:
                   res.status_code = 400
                   return {'detail' : 'Invalid status.'}

       resu = await payment_handler.record_maya_payment(rrn, relief_id, donor_id)

       if resu[1] == False:
             res.status_code = 400
             return {'detail': 'Payment was unsuccessful.'}

       return {'detail' : 'Payment successfully recorded'}