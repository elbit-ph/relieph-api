from typing import Annotated, List
from fastapi import APIRouter, Depends, UploadFile, HTTPException, status, Response, Body, Form
from dependencies import get_logger, get_current_user, get_code_email_handler, get_file_handler
from services.db.database import Session
from services.db.models import User, Address, UserUpgradeRequest, VerificationCode, SponsorshipRequest, Organization
from services.log.log_handler import LoggingService
from services.email.code_email_handler import CodeEmailHandler
from services.email.user_email_handler import UserEmailHandler
from services.storage.file_handler import FileHandler
from models.auth_details import AuthDetails
from util.auth.auth_tool import authorize
from util.auth.jwt_util import (
    get_hashed_password
)
from util.files.image_validator import is_image_valid
from pydantic import BaseModel, Json
from datetime import datetime, timedelta
from sqlalchemy import and_
import json
from types import SimpleNamespace
from util.code_generator import generate_code

router = APIRouter(
    prefix="/users",
    tags=["users"],
    dependencies=[]
)

db = Session()
file_handler = FileHandler()
user_email_handler = UserEmailHandler()
code_email_handler = CodeEmailHandler()

class NewAddressDTO(BaseModel):
    region: str
    city: str
    brgy: str
    street: str
    zipcode: int
    coordinates: str

class DetailResponse(BaseModel):
    detail:str
    
class RetrieveUserResponse(BaseModel):
    user_id: int
    # sponsor_user_id : int
    # firstname : str
    # lastname : str
    # level : int
    # is_verified : bool
    # profile : str
    

    def __init__(self, user:User, profile_link:str):
        super(BaseModel, self).__init__()
        self.user_id = user.id
        self.sponsor_id = user.sponsor_id
        self.firstname = user.first_name
        self.lastname = user.last_name
        self.level = user.level
        self.is_verified = user.is_verified
        self.profile = profile_link



@router.get("/")
async def retrieve_users(p: int = 1, c: int = 10):
    """
    Retrieves users (non-admin). Gets `c` amount of users according to `p` page
    """

    # Gets list of users
    users:List[User] = db.query(User).filter(and_(User.is_deleted == False, User.level < 4)).limit(c).offset((p-1)*c).all() 
    
    # initialize array of users
    to_return = []
    
    # iterate and only select necessary data from each user
    for user in users:
        profile_link = await file_handler.get_user_profile(user.id)
        to_return.append({
            "id" : user.id,
            "sponsor_id" : user.sponsor_id,
            "first_name" : user.first_name,
            "last_name" : user.last_name,
            "level" : user.level,
            "profile" : profile_link
        })

    # return user
    return to_return

@router.get("/{id}")
async def retrieve_user(id:int):
    """
    Retrieves a particular user, identified by `id`.
    """

    # finds user
    user:User = db.query(User).filter(and_(User.id == id, User.is_deleted == False)).first()

    # raise HTTP 404 error when user is not found
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )

    # get profile link from object store
    # returns default when no profile is set
    profile_link = await file_handler.get_user_profile(id)

    # returns relevant user data
    return {
        "id": user.id,
        "sponsor_id" : user.sponsor_id,
        "firstname" : user.first_name,
        "lastname" : user.last_name,
        "level" : user.level,
        "is_verified" : user.is_verified,
        "profile" : profile_link
    }


@router.get("/is-username-taken")
async def check_if_username_is_taken(username:str, res:Response):
    """
    Checks if username is already taken.
    """
    user:User = db.query(User).filter(and_(User.username == username, User.is_deleted == False)).first()
    # check if user with `username` exists
    if user is None:
        return False
    return True

@router.get("/is-email-taken")
async def check_if_email_is_taken(email:str, res:Response):
    """
    Checks if email is already taken
    """
    user:User = db.query(User).filter(and_(User.email == email, User.is_deleted == False)).first()
    # check if user with `email` exists
    if user is None:
        return False
    return True

class BasicUserDTO(BaseModel):
    fname: str
    lname: str
    username: str
    password: str
    confirmPassword: str
    email: str
    mobile: str

@router.post("/basic")
async def basic_signup(res: Response, body:BasicUserDTO):
    """
    Creates level 1 user.
    Requires `fname`, `lname`, `username`, `password`, `confirmPassword`, `email`, `mobile`.
    """

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

    # instantiates new user
    user = User()

    # enter data
    user.first_name = body.fname
    user.last_name = body.lname
    user.username = body.username
    user.password =  get_hashed_password(body.password)
    user.email = body.email
    user.mobile = body.mobile
    user.level = 1

    # save user to db
    db.add(user)
    db.commit()

    # create verification request
    verification_request:VerificationCode = VerificationCode()

    verification_request.code = generate_code()
    verification_request.reason = 'EMAIL_VERIFICATION'
    verification_request.user_id = user.id
    verification_request.expired_at = datetime.now() + timedelta(days=1)

    db.add(verification_request)
    db.commit()

    # send verification code to user
    ## thru email
    await code_email_handler.send_email_verfication_code(user.email, user.first_name, verification_request.code)

    # return HTTP 200
    return {
        "detail" : "Account successfully created."
    }

@router.post("/personal/verify/{user_email}")
async def verify_email(user_email:str, code:str, res:Response):
    """
    Verify user email.
    """

    # get user
    user:User = db.query(User).filter(User.email == user_email).first()

    # check if user exists, return HTTP 404 when non-existent
    if user is None:
        res.status_code = 404
        return {'detail' : 'User not found.'}
    
    # get verification code attributed to user (if existing)
    verification_code:VerificationCode = db.query(VerificationCode).filter(and_(VerificationCode.user_id == user.id, VerificationCode.reason == "EMAIL_VERIFICATION")).first()

    # check if verification request is non-existent, return HTTP 404 when true
    if verification_code is None:
        res.status_code = 404
        return {'detail' : 'No email verification request found.'}

    # check if entered code matches code in DB, return HTTP 400 when no
    if verification_code.code != code:
        res.status_code = 400
        return {'detail' : 'Nonmatching verification code.'}
    
    # set user to verified 
    user.is_verified = True

    # delete instance of verification code from db
    db.delete(verification_code)
    db.commit()

    return {'Successfully verified email.'}

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
async def upgrade_personal_account(res: Response, valid_id: UploadFile, body:UpgradeAccountDTO = Form(), user: AuthDetails = Depends(get_current_user)):
    """
    Upgrades user to account level 2
    """

    # check for authorization
    authorize(user, 1, 1) # only accounts of level 1 can upgrade to personal+

    # check if image upload is valid
    if is_image_valid(valid_id) == False:
        res.status_code = 400
        return {'detail' : 'Invalid image.'}

    # save valid id
    resu = await file_handler.upload_multiple_file([valid_id], user.user_id, 'valid_ids')

    # try to upload valid id
    if resu[1] == False:
        res.status_code = 500
        return {'detail': 'Error uploading image.'}

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

    return {'detail' : 'Successfully sent upgrade request.'}

@router.get("/upgrades/")
def retrieve_upgrade_requests(p: int = 1, c: int = 10, status:str = 'ALL', user: AuthDetails = Depends(get_current_user)):
    """
    Retrieve upgrade requests. Requires admin access.
    """
    
    # check user authorization
    authorize(user, 4, 4) # only admin can see upgrade requests
    
    # initializes request list
    requests = List[UserUpgradeRequest]

    match status.lower():
        case 'pending':
            requests = db.query(UserUpgradeRequest).filter(UserUpgradeRequest.status == 'PENDING').limit(c).offset((p-1)*c).all()
        case 'rejected':
            requests = db.query(UserUpgradeRequest).filter(UserUpgradeRequest.status == 'REJECTED').limit(c).offset((p-1)*c).all()
        case 'approved':
            requests = db.query(UserUpgradeRequest).filter(UserUpgradeRequest.status == 'APPROVED').limit(c).offset((p-1)*c).all()
        case _:
            # returns all when query is invalid
            requests = db.query(UserUpgradeRequest).limit(c).offset((p-1)*c).all()

    return requests

@router.get("/upgrades/{upgrade_request_id}/valid-id")
async def retrieve_valid_id(upgrade_request_id:int, res:Response, user: AuthDetails = Depends(get_current_user)):
    """
    Retrieve request valid id. Requires admin access.
    """
    
    # check if user is authorized
    authorize(user, 4, 4)

    upgrade_request:UserUpgradeRequest = db.query(UserUpgradeRequest).filter(and_(UserUpgradeRequest.id == upgrade_request_id)).first()
    
    # check if upgrade request exists
    if upgrade_request is None:
        res.status_code = 404
        return {'detail' : 'User upgrade request non-existing'}

    # retrieve valid id
    resu = await file_handler.retrieve_files(upgrade_request.user_id, 'valid_ids')

    # check if image retrieval was successful
    if resu[1] == False:
        res.status_code = 400
        return {'detail' : 'Error getting images'}
    
    # return file link
    return resu[0]

@router.get("/upgrades/{upgrade_request_id}")
async def retrieve_upgrade_request(res:Response, upgrade_request_id: int, user: AuthDetails = Depends(get_current_user)):
    """
    Retrieves particular user upgrade request via `upgrade_request_id`. Requires admin access.
    """

    # check user authorization
    authorize(user, 4, 4)

    # get user upgrade request from db
    request:UserUpgradeRequest = db.query(UserUpgradeRequest).filter(and_(UserUpgradeRequest.id == upgrade_request_id, UserUpgradeRequest.status == 'PENDING')).first()

    # check if request is existent
    if request is None:
       res.status_code = 404
       return {'detail' : 'Upgrade request not found.'}

    # initialize return body
    to_return = {
        'details' : request
    }

    # get valid id
    image_res = await file_handler.retrieve_files(request.user_id, f'valid_ids/{user.user_id}')

    if image_res[1] != False:
        # append valid id link to return body
        to_return['valid_id'] = image_res[0]

    return to_return

@router.post("/upgrades/{action}/{upgrade_request_id}")
async def resolve_upgrade_request(action:str, upgrade_request_id, res:Response, user: AuthDetails = Depends(get_current_user)):
    """
    Resolves (approve/reject) user upgrade request of `upgrade_request_id`. Requires admin access.
    """
    
    # check for user authorization
    authorize(user, 4, 4)

    # check if request exists
    upgrade_request:UserUpgradeRequest = db.query(UserUpgradeRequest).filter(and_(UserUpgradeRequest.id == upgrade_request_id, UserUpgradeRequest.status == 'PENDING')).first()

    # return HTTP 404 when upgrade request is non-existent
    if upgrade_request is None:
        res.status_code = 404
        return {'detail' : 'Upgrade request not found.'}
    
    # get user tied to user upgrade request
    user: User = db.query(User).filter(User.id == upgrade_request.user_id).first()

    match action.lower():
        case 'approve':
            upgrade_request.status = 'APPROVED'
            
            # increment user id
            user.level = 2
            await user_email_handler.send_upgrade_approval_notice(user.first_name, user.email)
        case 'reject':
            upgrade_request.status = 'REJECTED'
            await user_email_handler.send_upgrade_rejection_notice(user.first_name, user.email)
        case _:
            # return HTTP 406 when action is not allowed
            res.status_code = 406
            return {'detail' : 'Action not allowed.'}
    
    # update user upgrade request `updated_at`
    upgrade_request.updated_at = datetime.now()

    db.commit()

    return {'detail' : 'Successfully resolved upgrade request.'}

class EditUserDetailsDTO(BaseModel):
    email:str = None
    mobile:str = None

@router.patch("/details")
async def edit_user_details(body:EditUserDetailsDTO, res:Response, user: AuthDetails = Depends(get_current_user)):
    """
    Edits user details.
    """
    
    # check for authorization
    authorize(user, 1, 4)

    # get user
    user_:User = db.query(User).filter(User.id == user.user_id).first()

    # edit details
    user_.email = body.email if body.email != None and body.email != "" else user_.email
    user_.mobile = body.mobile if body.mobile != None and body.mobile != "" else user_.mobile

    # save changes
    db.commit()

    return {'detail': 'Successfully edited user details.'}

@router.patch("/address")
async def edit_user_address(res: Response, body: NewAddressDTO, user: AuthDetails = Depends(get_current_user)):#
    """
    Edits user's address.
    """

    # checks for authorization. Only applicable for users levels `2` to `4`
    authorize(user, 2,4)

    # retrieves relief_address
    relief_address:Address = db.query(Address).filter(and_(Address.owner_type == 'USER', Address.owner_id == user.user_id)).first()

    # edit only those relevant
    relief_address.region = relief_address.region if body.region == "" else body.region
    relief_address.city = relief_address.city if body.city == "" else body.city
    relief_address.brgy = relief_address.brgy if body.brgy == "" else body.brgy
    relief_address.street = relief_address.street if body.street == "" else body.street
    relief_address.zipcode = relief_address.zipcode if body.zipcode == "" else body.zipcode
    relief_address.coordinates = relief_address.coordinates if body.coordinates == "" else body.coordinates
    relief_address.updated_at = datetime.now()

    db.commit()

    return {
        "detail": "Relief address successfully edited."
    }

@router.post("/profile")
async def save_user_profile(image: UploadFile, res:Response, user: AuthDetails = Depends(get_current_user)):
    """
    Saves and sets user's profile image of user.
    """
    # checks for authorization
    authorize(user, 1, 4)
    
    # checks if file has valid suffix, returns HTTP 400 if invalid
    if file_handler.is_file_valid(image, file_handler.allowed_img_suffix) == False:
        res.status_code = 400
        return {"detail" : "Invalid image format."}

    # check if file already exists
    if file_handler.file_exists(user.user_id, 'users') == True:
        # delete existing image before uploading
        await file_handler.remove_file(user.user_id, 'users')

    # upload file
    await file_handler.upload_file(image, user.user_id, 'users')

    return {
        "detail": "Profile successfully uploaded."
    }

# get user profile
@router.get("/{id}/profile")
async def retrieve_user_profile_image(id:int, res: Response):
    """
    Returns user profile image.
    """

    # check if user exists, return HTTP 404 if non-existent
    if db.query(User).filter(and_(User.id == id, User.is_deleted == False, User.is_verified == True)).first() == None:
        res.status_code = 404
        return {'detail' : 'User not found.'}

    # get profile link
    profile_link = await file_handler.get_user_profile(id)

    return profile_link

@router.delete("/{id}")
async def delete_user(id:int, res: Response, user:AuthDetails = Depends(get_current_user)):
    # checks for user authorization
    authorize(user, 1,4)
    
    # check first if current user is the current user or has admin privileges
    if id != user.user_id and user.level != 5:
        res.status_code = 403
        return {
            "detail": "Insufficient authorization to delete user."
        }
    
    user:User = db.query(User).filter(User.id == user.user_id).first()
    # sets user.is_deleted to `True`
    user.is_deleted = True

    db.commit()

    return {
        "detail" : "Successfully deleted user."
    }

class UserSponsorshipRequestDTO(BaseModel):
    foundation_id : int
    message: str

@router.post("/{id}/sponsorship")
async def apply_for_sponsorship(body:UserSponsorshipRequestDTO, res:Response, user:AuthDetails = Depends(get_current_user)):
    """
    Allows user to apply for sponsorship in foundation
    """

    # check for user authorization
    authorize(user, 2, 2)

    request = SponsorshipRequest()

    foundation = db.query(Organization).filter(and_(Organization.id == body.foundation_id, Organization.tier == 2)).first()

    # check if foundation exists
    if foundation is None:
        res.status_code = 404
        return {'detail': 'Foundation not found'}
    
    request = db.query(SponsorshipRequest).filter(and_(SponsorshipRequest.status == 'PENDING', SponsorshipRequest.owner_id == user.user, SponsorshipRequest.owner_type == 'USER')).first()

    # check if there's an existing request for user
    if request is not None:
        res.status_code = 400
        return {'detail': 'Existing request'}
    
    # create new sponsorship request
    request = SponsorshipRequest()

    request.foundation_id = body.foundation_id
    request.owner_id = user.user_id
    request.owner_type = 'USER'
    request.message = body.message
    request.status = 'PENDING'

    db.add(request)
    db.commit()

    return {'detail' : 'Successfully sent request for sponsorship'}
