from typing import Annotated
from fastapi import APIRouter, Depends, UploadFile, HTTPException, status, Response, Body
from dependencies import get_db_session, get_logger, get_s3_handler, get_current_user
from services.db.database import Session
from services.db.models import User, Address
from services.log.log_handler import LoggingService
from services.aws.s3_handler import S3_Handler
from models.auth_details import AuthDetails
from util.auth.auth_tool import authorize
from util.auth.jwt_util import (
    get_hashed_password
)
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(
    prefix="/users",
    tags=["users"],
    dependencies=[Depends(get_db_session), Depends(get_logger)]
)

DB = Annotated[Session, Depends(get_db_session)]
Logger = Annotated[LoggingService, Depends(get_logger)]
S3Handler = Annotated[S3_Handler, Depends(get_s3_handler)]

@router.get("/")
def retrieveUsers(db: DB, p: int = 1, c: int = 10):
    return db.query(User).limit(c).offset((p-1)*c).all()

@router.get("/{id}")
def retrieveUser(db:DB, id:int):
    user:User = db.query(User).filter(User.id == id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )
    return {
        "id": user.id,
        "firstname" : user.first_name,
        "lastname" : user.last_name
    }

class CreateAnonymousUserDTO(BaseModel):
    username:str
    email:str

@router.post("/anonymous")
def createAnonymousUser(db:DB, body:CreateAnonymousUserDTO):
    newUser = User()
    newUser.username = body.username
    newUser.email = body.email

    # add user to db
    db.add(newUser)
    db.commit()

    return {
        "detail": "success"
    }

class UpgadeUserDTO(BaseModel):
    fname: str
    lname: str
    password: str
    confirmPassword: str
    mobile: str

@router.post("/anonymous/{email}")
def UpgradeUser(db:DB, email:str, res: Response, body: UpgadeUserDTO):
    user:User = db.query(User).filter(User.email == email).first()

    # check if user is in db to begin with
    if user is None:
        res.status_code = 400
        return {"detail": "Non-existing user"}
    
    if body.password != body.confirmPassword:
        res.status_code = 400
        return {"detail": "Passwords don't match"}

    user.first_name = body.fname
    user.last_name = body.lname
    user.password = get_hashed_password(body.password)
    user.mobile = body.mobile
    user.level = 1
    user.updated_at = datetime.now()

    db.commit()

    return {"detail": "success"}

class BasicUserDTO(BaseModel):
    fname: str
    lname: str
    username: str
    password: str
    confirmPassword: str
    email: str
    mobile: str

@router.post("/basic")
def createBasicUser(db:DB, res: Response, body:BasicUserDTO):
    # check if email is already used  
    if db.query(User).filter(User.email == body.email).first() != None:
        res.status_code = 400
        return {
            "detail" : "Email already used."
        }
    
    # check if username is already used  
    if db.query(User).filter(User.username == body.username).first() != None:
        res.status_code = 400
        return {
            "detail" : "Username already used."
        }

    # check if passwords match
    if body.password != body.confirmPassword:
        res.status_code = 400
        return {
            "detail": "Mismatched passwords"
        }

    user = User()

    user.first_name = body.fname
    user.last_name = body.lname
    user.username = body.username
    user.password =  get_hashed_password(body.password)
    user.email = body.email
    user.mobile = body.mobile
    user.level = 1
    # assign default user profiledir ater

    # save
    db.add(user)
    db.commit()

    # also return id    
    return {
        "detail" : "Account successfully created"
    }

class NewAddressDTO(BaseModel):
    region: str
    city: str
    brgy: str
    zipcode: str
    coordinates: str

@router.post("/{id}/address")
async def saveUserAddress(db:DB, id: int, addressDto: NewAddressDTO, user: AuthDetails = Depends(get_current_user)):
    authorize(user, 2,5)

    if id != user.user_id:
        raise HTTPException(
            status_code=403,
            detail="Unauthorized action."
        )

    newAddress = Address()
    
    newAddress.owner_id = id
    newAddress.owner_type = "USER"
    newAddress.region = addressDto.region
    newAddress.city = addressDto.city
    newAddress.brgy = addressDto.brgy
    newAddress.zipcode = addressDto.zipcode
    newAddress.coordinates = addressDto.coordinates

    db.add(newAddress)
    db.commit()

    return {
        "detail": "success"
    }

@router.post("/profile")
async def saveUserProfile(image: UploadFile, db:DB, s3:S3Handler, user: AuthDetails = Depends(get_current_user)):
    # get user id from authentication
    authorize(2,5)

    # check if file already exists
    img = s3.get_image(user.user_id, 'users')

    if (img is not None):
        # delete currently saved
        await s3.delete_image(user.user_id, 'users')
        # save new profile
        await s3.upload_single_image(image, user.user_id, 'users')
        return {
            "detail": "Profile successfully updated."
        }

    await s3.upload_single_image(image, user.user_id, 'users')

    return {
        "detail": "Profile successfully uploaded."
    }

# get user profile
@router.get("/{id}/profile")
def retrieveUserProfile(id:int, res: Response, s3: S3Handler):
    resu = s3.get_image(id, 'users')

    if resu[1] != True:
        res.status_code = 400
        return {'Error':'Invalid'}
     
    return {
        'link': resu[0]
    }

@router.post("/{id}/level/{to}")
async def changeLevel(db:DB, id:int, to:int, user: AuthDetails = Depends(get_current_user)):
    # check if user is admin
    authorize(user, 5, 5)

    # change level here
    user:User = db.query(User).filter(User.id == id).first()
    
    # assign new level
    user.level = to

    return {
        "detail": "success"
    }

@router.delete("/{id}")
async def deleteUser(db:DB, id:int, res: Response, user:AuthDetails = Depends(get_current_user)):
    # check first if current user is similar to user
    if (id != user.user_id):
        res.status_code = 403
        return {
            "detail": "Forbidden access"
        }

    user:User = db.query(User).filter(User.id == user.user_id).first()
    user.is_deleted = True

    db.commit()

    return {
        "detail" : "success"
    }