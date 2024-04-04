from typing import Annotated, List
from fastapi import APIRouter, Depends, UploadFile, HTTPException, status, Response, Body, Form
from dependencies import get_db_session, get_logger, get_s3_handler, get_current_user
from services.db.database import Session
from services.db.models import User, Address, UserUpgradeRequest
from services.log.log_handler import LoggingService
from services.aws.s3_handler import S3_Handler
from models.auth_details import AuthDetails
from util.auth.auth_tool import authorize
from util.auth.jwt_util import (
    get_hashed_password
)
from util.files.image_validator import is_image_valid
from pydantic import BaseModel, Json
from datetime import datetime
from sqlalchemy import and_
import json
from types import SimpleNamespace

router = APIRouter(
    prefix="/users",
    tags=["users"],
    dependencies=[Depends(get_db_session), Depends(get_logger)]
)

DB = Annotated[Session, Depends(get_db_session)]
Logger = Annotated[LoggingService, Depends(get_logger)]
S3Handler = Annotated[S3_Handler, Depends(get_s3_handler)]

class NewAddressDTO(BaseModel):
    region: str
    city: str
    brgy: str
    street: str
    zipcode: int
    coordinates: str

@router.get("/")
async def retrieveUsers(db: DB, s3:S3Handler, p: int = 1, c: int = 10):
    # truncate sensitive data - 
    users = db.query(User.id, User.sponsor_id, User.first_name, User.last_name, User.level).limit(c).offset((p-1)*c).all() 
    to_return = []
    for user in users:
        # append image link
        profile_link = s3.get_image(user[0], 'users')
        to_return.append({
            "id" : user[0],
            "sponsor_id" : user[1],
            "first_name" : user[2],
            "last_name" : user[3],
            "level" : user[4],
            "profile" : profile_link[0] if profile_link[1] != False else None
        })
    return to_return

@router.get("/{id}")
async def retrieveUser(db:DB, id:int, s3:S3Handler):
    user:User = db.query(User).filter(User.id == id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )
    
    profile_link = await s3.get_image(id, 'users')

    if profile_link[1] == False:
        profile_link[0] = 'other link'

    return {
        "id": user.id,
        "sponsor_id" : user.sponsor_id,
        "firstname" : user.first_name,
        "lastname" : user.last_name,
        "level" : user.level,
        "profile" : profile_link[0]
    }

class BasicUserDTO(BaseModel):
    fname: str
    lname: str
    username: str
    password: str
    confirmPassword: str
    email: str
    mobile: str

@router.post("/personal")
async def regular_signup(db:DB, res: Response, profile: UploadFile, s3:S3Handler, body:Json = Form()):
    body:BasicUserDTO = json.loads(json.dumps(body), object_hook=lambda d: SimpleNamespace(**d))

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
    
    # check if image is valid
    if is_image_valid(profile) == False:
        res.status_code = 400
        return {
            "detail" : "Invalid profile image format."
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

    resu = await s3.upload_single_image(profile, user.id, 'users')

    if resu[1] == False:
        print(f'Profile of user {id} not added correctly.')

    # also return id    
    return {
        "detail" : "Account successfully created."
    }

class UpgradeAccountDTO(BaseModel):
    first_name :str
    last_name :str
    birthday: datetime
    sex: str
    accountno: str
    id_type: str
    # address info
    region: str
    city: str
    brgy: str
    street: str
    zipcode: int
    coordinates: str

@router.post("/upgrades")
async def upgrade_personal_account(db:DB, res: Response, valid_id: UploadFile, s3:S3Handler, body:Json = Form(), user: AuthDetails = Depends(get_current_user)):
    authorize(user, 1, 1) # only accounts of level 1 can upgrade to personal+

    body:UpgradeAccountDTO = json.loads(json.dumps(body), object_hook=lambda d: SimpleNamespace(**d))

    # validate input
    if is_image_valid(valid_id) == False:
        res.status_code = 400
        return {'detail' : 'Invalid image.'}

    # create account upgrade request
    upgrade_request = UserUpgradeRequest()
    
    upgrade_request.user_id = user.user_id
    upgrade_request.first_name = body.first_name
    upgrade_request.last_name = body.last_name
    upgrade_request.birthday = body.birthday
    upgrade_request.sex = body.sex
    upgrade_request.accountno = body.accountno
    upgrade_request.id_type = body.id_type

    # save address
    address = Address()

    address.owner_id = user.user_id
    address.owner_type = 'USER'
    address.region = body.region
    address.city = body.city
    address.brgy = body.brgy
    address.street = body.street
    address.zipcode = body.zipcode
    address.coordinates = body.coordinates

    db.add(upgrade_request)
    db.add(address)
    db.commit()
    
    # save valid id
    image_upload_res = await s3.upload_multiple([valid_id], user.user_id, f'valid_ids/{user.user_id}')

    return {'detail' : 'Successfully sent upgrade request.'}

# get list of upgrade requests
@router.get("/upgrades/")
def retrieve_upgrade_requests(db:DB, p: int = 1, c: int = 10, status:str = 'ALL', user: AuthDetails = Depends(get_current_user)):
    authorize(user, 4, 4) # only admin can see upgrade requests
    
    requests = List[UserUpgradeRequest]

    match status.lower():
        case 'pending':
            requests = db.query(UserUpgradeRequest).filter(UserUpgradeRequest.status == 'PENDING').limit(c).offset((p-1)*c).all()
        case 'rejected':
            requests = db.query(UserUpgradeRequest).filter(UserUpgradeRequest.status == 'REJECTED').limit(c).offset((p-1)*c).all()
        case 'approved':
            requests = db.query(UserUpgradeRequest).filter(UserUpgradeRequest.status == 'APPROVED').limit(c).offset((p-1)*c).all()
        case _:
            requests = db.query(UserUpgradeRequest).limit(c).offset((p-1)*c).all()

    return requests

@router.get("/upgrades/{upgrade_request_id}")
async def retrieve_upgrade_request(db:DB, s3:S3Handler, res:Response, upgrade_request_id: int, user: AuthDetails = Depends(get_current_user)):
    authorize(user, 4, 4) 

    request:UserUpgradeRequest = db.query(UserUpgradeRequest).filter(and_(UserUpgradeRequest.id == upgrade_request_id, UserUpgradeRequest.status == 'PENDING')).first()

    if request is None:
       res.status_code = 404
       return {'detail' : 'Upgrade request not found.'}

    to_return = {
        'details' : request
    }

    # get images
    image_res = await s3.retrieve_multiple(request.user_id, f'valid_ids/{user.user_id}')

    if image_res[1] != False:
        to_return['valid_id'] = image_res[0]

    return to_return

@router.post("/upgrades/{action}/{upgrade_request_id}")
async def resolve_upgrade_request(db:DB, action:str, upgrade_request_id, res:Response, user: AuthDetails = Depends(get_current_user)):
    authorize(user, 4, 4)

    # check if requests exists
    upgrade_request:UserUpgradeRequest = db.query(UserUpgradeRequest).filter(and_(UserUpgradeRequest.id == upgrade_request_id, UserUpgradeRequest.status == 'PENDING')).first()

    if upgrade_request is None:
        res.status_code = 404
        return {'detail' : 'Upgrade request not found.'}
    
    user: User = db.query(User).filter(User.id == upgrade_request.user_id).first()

    match action.lower():
        case 'approve':
            upgrade_request.status = 'APPROVED'
            
            # increment user id
            user.level = 2
        case 'reject':
            upgrade_request.status = 'REJECTED'
        case _:
            res.status_code = 406
            return {'detail' : 'Action not allowed.'}
    upgrade_request.updated_at = datetime.now()

    db.commit()

    # send email to user

    return {'detail' : 'Successfully resolved upgrade request.'}

@router.patch("/address")
async def editUserAddress(db:DB, res: Response, body: NewAddressDTO, user: AuthDetails = Depends(get_current_user)):#
    authorize(user, 2,4)

    relief_address:Address = db.query(Address).filter(and_(Address.owner_type == 'USER', Address.owner_id == user.user_id)).first()

    null_at_first = False

    if relief_address is None:
        relief_address = Address()
        relief_address.owner_id = user.user_id
        relief_address.owner_type = 'USER'
        null_at_first = True

    relief_address.region = relief_address.region if body.region is "" else body.region
    relief_address.city = relief_address.city if body.city is "" else body.city
    relief_address.brgy = relief_address.brgy if body.brgy is "" else body.brgy
    relief_address.street = relief_address.street if body.street is "" else body.street
    relief_address.zipcode = relief_address.zipcode if body.zipcode is "" else body.zipcode
    relief_address.coordinates = relief_address.coordinates if body.coordinates is "" else body.coordinates
    relief_address.updated_at = datetime.now()

    if null_at_first:
        db.add(relief_address)

    db.commit()

    return {
        "detail": "Relief address successfully edited."
    }

@router.post("/profile")
async def saveUserProfile(image: UploadFile, res:Response, db:DB, s3:S3Handler, user: AuthDetails = Depends(get_current_user)):
    # get user id from authentication
    authorize(user, 1, 4)

    if is_image_valid(image) == False:
        res.status_code = 400
        return {"detail" : "Invalid image format."}

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
        return {'Error':'User profile retrieval failed.'}
     
    return {
        'link': resu[0]
    }

@router.delete("/{id}")
async def deleteUser(db:DB, id:int, res: Response, user:AuthDetails = Depends(get_current_user)):
    authorize(user, 1,4)
    
    # check first if current user is similar to user
    if id != user.user_id and user.level != 5:
        res.status_code = 403
        return {
            "detail": "Insufficient authorization to delete user."
        }

    user:User = db.query(User).filter(User.id == user.user_id).first()
    user.is_deleted = True

    db.commit()

    return {
        "detail" : "Successfully deleted user."
    }