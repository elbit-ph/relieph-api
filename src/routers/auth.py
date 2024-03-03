from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from dependencies import get_db_session, get_logger, get_s3_handler
from services.db.database import Session
from services.db.models import User
from services.log.log_handler import LoggingService
from services.aws.s3_handler import S3_Handler
from util.auth.jwt_util import (
    verify_password,
    create_access_token,
    create_refresh_token
)

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
    dependencies=[Depends(get_db_session), Depends(get_logger)]
)

DB = Annotated[Session, Depends(get_db_session)]
Logger = Annotated[LoggingService, Depends(get_logger)]
S3Handler = Annotated[S3_Handler, Depends(get_s3_handler)]

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