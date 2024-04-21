import os
from dotenv import load_dotenv
import requests
from requests import Response
from sqlalchemy import and_, or_
from services.db.models import ReliefPaymentKey, ReceivedMoney, ReliefEffort
from base64 import urlsafe_b64encode
from cryptography.fernet import Fernet
from services.db.database import Session
import secrets

load_dotenv()

class PaymentHandler():
    def __init__(self, redirect_url:str):
        self.redirect_url = redirect_url
        self.maya_checkout_link = "https://pg-sandbox.paymaya.com/checkout/v1/checkouts" # currently set to sandbox mode
        self.maya_retrieve_payment_by_rrn_link = "https://pg-sandbox.paymaya.com/payments/v1/payment-rrns/"
        self.db = Session()
        self.base_url = os.environ['BASE_URL']
        self.redirect_url = f'{os.environ["BASE_URL"]}/api/monetary/redirect'

    # function that creates a Maya Checkout Link
    async def create_payment_session(self, relief_effort_id:int, amount:float, donor_id:int = 0):
        # find relief effort
        relief_effort:ReliefEffort = self.db.query(ReliefEffort).filter(and_(ReliefEffort.id == relief_effort_id, ReliefEffort.is_deleted == False, ReliefEffort.is_active == True)).first()

        # return error when relief effort not found
        if relief_effort is None:
            return ('ReliefEffortNonexistent', False)

        # obtain api key
        relief_payment_key:ReliefPaymentKey = self.db.query(ReliefPaymentKey).filter(and_(ReliefPaymentKey.owner_id == relief_effort.owner_id, ReliefPaymentKey.owner_type == relief_effort.owner_type)).first()

        if relief_payment_key is None:
            return  ('PaymentKeyNonexistent', False)

        fernet = Fernet(os.environ['ENCRYPTION'])

        # decrypt public key
        p_key = fernet.decrypt(relief_payment_key.p_key.encode())
        b64_encoded_p_key = urlsafe_b64encode(p_key).decode()

        # use api key to obtain checkout link
        rrn = secrets.token_urlsafe(16)
        response:Response = requests.post(
                                url=self.maya_checkout_link,
                                json = {
                                    "totalAmount" : {
                                        "value" : amount,
                                        "currency" : "PHP"
                                    },
                                    "requestReferenceNumber" : rrn,
                                    "redirectUrl" : {
                                        "success" : f'{self.redirect_url}?status=success&rrn={rrn}&relief_id={relief_effort_id}&donor_id={donor_id}',
                                        "failure" : f'{self.redirect_url}?status=failure&rrn={rrn}&relief_id={relief_effort_id}&donor_id={donor_id}',
                                        "cancel" : f'{self.redirect_url}?status=cancel&rrn={rrn}&relief_id={relief_effort_id}&donor_id={donor_id}'
                                    }
                                },
                                headers= {
                                    "accept": "application/json",
                                    "content-type" : "application/json",
                                    "authorization" : f'Basic {b64_encoded_p_key}'
                                }
                            )
        # if not success, return ErrorGenerating response
        if response.status_code != 200:
            return ('ErrorGenerating', False)

        # return checkout link if successful
        return (response.json(), True)
    
    # function that saves payment record to db
    # 0 donor id denotes anonymous donation
    async def record_maya_payment(self, rrn, relief_id = 0, donor_id = 0):
        # find relief effort
        relief_effort:ReliefEffort = self.db.query(ReliefEffort).filter(and_(ReliefEffort.id == relief_id, ReliefEffort.is_deleted == False, ReliefEffort.is_active == True)).first()

        # return error when relief effort not found
        if relief_effort is None:
            return ('ReliefEffortNonexistent', False)

        # obtain api key
        relief_payment_key:ReliefPaymentKey = self.db.query(ReliefPaymentKey).filter(and_(ReliefPaymentKey.owner_id == relief_effort.owner_id, ReliefPaymentKey.owner_type == relief_effort.owner_type)).first()

        if relief_payment_key is None:
            return  ('PaymentKeyNonexistent', False)
        
        fernet = Fernet(os.environ['ENCRYPTION'])

        s_key = fernet.decrypt(relief_payment_key.s_key.encode())
        b64_encoded_s_key = urlsafe_b64encode(s_key).decode()

        print(s_key)

        res:Response = requests.get(
            url = f'{self.maya_retrieve_payment_by_rrn_link}{rrn}',
            headers={
                "accept": "application/json",
                "authorization" : f'Basic {b64_encoded_s_key}'
            }
        )

        if res.status_code != 200:
            return ('ErrorGetting', False)

        res_body = res.json()

        if res_body[0]['isPaid'] == False:
            return ('PaymentUnsuccessful', False)

        received = ReceivedMoney()

        received.donor_id = donor_id
        received.relief_id = relief_id
        received.platform = 'MAYA'
        received.amount = res_body[0]['amount']
        received.reference_no = rrn

        self.db.add(received)

        self.db.commit()

        return ('Success', True)
    
    # function that encrypts and saves api key to db
    async def save_maya_api_key(self, owner_id:int, owner_type:str, pkey:str, skey:str):
        # get owner
        relief_payment_key:ReliefPaymentKey = self.db.query(ReliefPaymentKey).filter(and_(ReliefPaymentKey.owner_id == owner_id, ReliefPaymentKey.owner_type == owner_type)).first()

        if relief_payment_key is not None:
            return ('ExistingKey', False)

        fernet = Fernet(os.environ['ENCRYPTION'])

        # create new instance of relief_payment_key
        relief_payment_key = ReliefPaymentKey()

        relief_payment_key.owner_id = owner_id
        relief_payment_key.owner_type = owner_type
        relief_payment_key.p_key = fernet.encrypt(str.encode(pkey)).decode()
        relief_payment_key.s_key = fernet.encrypt(str.encode(skey)).decode()
        
        self.db.add(relief_payment_key)

        self.db.commit()

        return ('Success', True)