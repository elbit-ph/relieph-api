from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.security import OAuth2PasswordRequestForm
from dependencies import get_db_session, get_logger, get_current_user, get_email_handler, get_code_email_handler
from services.db.database import Session
from services.db.models import User, VerificationCode
from services.log.log_handler import LoggingService
from services.email.email_handler import EmailHandler
from services.email.code_email_handler import CodeEmailHandler
from util.auth.jwt_util import (
    get_hashed_password,
    verify_password,    
    create_access_token,
    create_refresh_token
)
from util.code_generator import generate_code
from util.auth.auth_tool import authorize
from pydantic import BaseModel
from datetime import datetime, timedelta
from pytz import UTC as utc
import requests
from sqlalchemy import and_
from dotenv import load_dotenv
import os

load_dotenv()

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
    dependencies=[Depends(get_db_session), Depends(get_logger)]
)

class ForgotPasswordDTO(BaseModel):
    email:str

DB = Annotated[Session, Depends(get_db_session)]
Logger = Annotated[LoggingService, Depends(get_logger)]
Email_Handler = Annotated[EmailHandler, Depends(get_email_handler)]
code_email_handler = Annotated[CodeEmailHandler, Depends(get_code_email_handler)]

# user levels
# 0/None - Guest/Anonymous
# 1 - Personal Accounts
# 2 - Personal+ accounts (verified)
# 3 - Organization Holder
# 4 - Admin/Moderator

@router.post('/login', summary="Create access and refresh tokens for user")
async def login(db:DB, form_data: OAuth2PasswordRequestForm = Depends()):
    user:User = db.query(User).filter(User.username==form_data.username).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect username or password"
        )

    hashed_pass = user.password
    if not verify_password(form_data.password, hashed_pass):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect username or password"
        )
    
    return {
        "access_token": create_access_token(user.username, user.level),
        "refresh_token": create_refresh_token(user.username, user.level),
    }

@router.post("/forgot-password", summary="Creates password reset request and sends verification code to user's email.")
async def forgot_password(email: ForgotPasswordDTO, db:DB, emailer:code_email_handler):
    user:User = db.query(User).filter(User.email == email.email).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User non-existent"
        )
    # generate code
    code = generate_code()
    # store code to db
    
    vcode_req = VerificationCode(code=code,reason="PASSWORD-RESET",user_id=user.id,expired_at=datetime.utcnow() + timedelta(minutes=30))
    print(vcode_req.reason)
    db.add(vcode_req)
    db.commit()

    # send email
    resp = await emailer.send_password_reset_code(email.email, f'{user.first_name} {user.last_name}', code)

    return 'Success'

class VerifyCodeModel(BaseModel):
    email: str
    code: str

# verify code
@router.get("/verify-code", summary="Checks if entered code is valid. Returns user id (securely store then use in /reset-password).")
async def verify_code(body:VerifyCodeModel, db:DB, response:Response):
    # get code
    #code_:VerificationCode = db.query(VerificationCode).filter(VerificationCode.code == body.code and VerificationCode.user_id == body.id).first()
    code_:VerificationCode = db.query(VerificationCode).join(User).filter(VerificationCode.code == body.code and User.email == body.email and VerificationCode.user_id == User.id).first()
    if code_ is None:
        # check if code is right
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code."
        )
    if code_.expired_at < utc.localize(datetime.utcnow()):
        # expired code
        db.delete(code_)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Expired code."
        )
    # returns user's id
    response.status_code = status.HTTP_202_ACCEPTED
    return {"userId" : code_.user_id}

class PasswordResetModel(BaseModel):
    id: int
    code: str
    password: str
    confirm_password: str

@router.patch("/reset-password", summary="Resets user's password.")
async def verify_code(body:PasswordResetModel, db:DB, response:Response):
    # get code
    code:VerificationCode = db.query(VerificationCode).filter(VerificationCode.user_id == body.id and body.code == VerificationCode.code).first()
    
    # check if code is right
    if code is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code."
        )
    if code.expired_at < utc.localize(datetime.utcnow()):
        db.delete(code)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Expired code."
        )
    if body.password != body.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords mismatch"
        )

    user:User = db.query(User).filter(User.id == body.id).first()
    user.password = get_hashed_password(body.password)
    user.updated_at = datetime.utcnow()
    db.delete(code)
    db.commit()
    # set to HTTP 202
    response.status_code = status.HTTP_202_ACCEPTED
    return {} # code should be sent again to allow change password functionality

@router.get("/get-authorized")
def test_authorized(user: User = Depends(get_current_user)):
    authorize(user, 1, 5)
    return {"Hello": "World"}

# Google authentication part

GOOGLE_CLIENT_ID =  os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")

@router.get("/login/google")
async def login_google():
    return {
        "url": f"https://accounts.google.com/o/oauth2/auth?response_type=code&client_id={GOOGLE_CLIENT_ID}&redirect_uri={GOOGLE_REDIRECT_URI}&scope=openid%20profile%20email&access_type=offline"
    }

@router.get("/auth/google")
def auth_google(code: str, prompt:str, db:DB):
    print(code)
    token_url = "https://accounts.google.com/o/oauth2/token"
    data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": f'{os.environ.get("BASE_URL")}/api/auth/auth/google',
        "grant_type": "authorization_code",
    }
    response = requests.post(token_url, data=data)
    access_token = response.json().get("access_token")
    user_info = requests.get("https://www.googleapis.com/oauth2/v1/userinfo", headers={"Authorization": f"Bearer {access_token}"})

    user_info = user_info.json()

    # generate token from user info 
    user:User = db.query(User).filter(and_(User.email == user_info['email'], User.is_deleted == False)).first()

    if user is None:
        # creates new user
        user = User()
        user.first_name = user_info['given_name']
        user.last_name = user_info['family_name']
        user.username = user_info['email'].split('@')[0]
        user.email = user_info['email']
        user.level = 1
        user.password = user_info['id']
        user.is_verified = True
        
        db.add(user)
        db.commit()
    
    # generate token from details
    return {
        "userInfo" : user_info,
        "token" : create_access_token(user.username, user.level)
    }