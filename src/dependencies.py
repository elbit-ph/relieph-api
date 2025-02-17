# imported libraries
from typing import Annotated
from fastapi import Header, HTTPException, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from datetime import datetime
from pydantic import ValidationError
import os
# user generated
from services.db.database import Session
from services.db.models import User
# from services.storage.cache_handler import CacheHandler
from services.email.email_handler import EmailHandler
from services.email.relief_email_handler import ReliefEmailHandler
from services.email.organization_email_handler import OrganizationEmailHandler
from services.email.code_email_handler import CodeEmailHandler
from services.log.log_handler import LoggingService
from services.storage.file_handler import FileHandler
from models.auth_details import AuthDetails
import jwt

# dependencies go here

async def get_db_session():
    return Session()

# async def get_cache_handler():
#     return CacheHandler()

async def get_email_handler():
    return EmailHandler()

async def get_relief_email_handler():
    return ReliefEmailHandler()

async def get_organization_email_handler():
    return OrganizationEmailHandler()

async def get_code_email_handler():
    return CodeEmailHandler()

def get_logger():
    return LoggingService('file.log')

def get_file_handler():
    return FileHandler()

reuseable_oauth = OAuth2PasswordBearer(
        tokenUrl="auth/login",
        scheme_name="JWT"
    )

# on a later date, try to place this on a separate python file
async def get_current_user(token: str = Depends(reuseable_oauth)) -> AuthDetails:
    try:
        payload = jwt.decode(
            token, os.environ['JWT_SECRET_KEY'], algorithms=['HS256']
        )
        
        if datetime.fromtimestamp(payload['exp']) < datetime.now():
            raise HTTPException(
                status_code = status.HTTP_401_UNAUTHORIZED,
                detail="Token expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except(jwt.PyJWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    db = await get_db_session()
    
    user:User = db.query(User).filter(User.username==payload['sub']).first()
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Could not find user",
        )
    
    return AuthDetails(user.id, user.username, user.level)