from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.security import OAuth2PasswordRequestForm
from dependencies import get_db_session, get_logger, get_s3_handler, get_current_user, get_email_handler, get_cache_handler
from services.db.database import Session
from services.db.models import User, VerificationCode
from services.log.log_handler import LoggingService
from services.aws.s3_handler import S3_Handler
from services.email.email_handler import EmailHandler
from services.storage.cache_handler import CacheHandler
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

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
    dependencies=[Depends(get_db_session), Depends(get_logger)]
)

class ForgotPasswordDTO(BaseModel):
    email:str

DB = Annotated[Session, Depends(get_db_session)]
Logger = Annotated[LoggingService, Depends(get_logger)]
S3Handler = Annotated[S3_Handler, Depends(get_s3_handler)]
Email_Handler = Annotated[EmailHandler, Depends(get_email_handler)]
Cache_Handler = Annotated[CacheHandler, Depends(get_cache_handler)]

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
async def forgot_password(email: ForgotPasswordDTO, db:DB, email_handler:Email_Handler, cache_handler:Cache_Handler):
    user:User = db.query(User).filter(User.email == email.email).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User non-existent"
        )
    # generate code
    code = generate_code()
    # store code to db
    #cache_handler.set(f'pwr-{user.id}', code)
    vcode_req = VerificationCode(code=code,reason="PASSWORD-RESET",user_id=user.id,expired_at=datetime.utcnow() + timedelta(minutes=30))
    print(vcode_req.reason)
    db.add(vcode_req)
    db.commit()

    # send email
    resp = await email_handler.send_code(email.email, f'{user.first_name} {user.last_name}', code)

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