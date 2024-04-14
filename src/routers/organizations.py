from typing import Annotated, List
from fastapi import APIRouter, Depends, UploadFile, HTTPException, status, Response, Body, Form
from dependencies import get_db_session, get_logger, get_current_user, get_organization_email_handler, get_file_handler
from services.db.database import Session
from services.db.models import Organization, User, Address, SponsorshipRequest
from services.log.log_handler import LoggingService
from services.storage.file_handler import FileHandler
from services.email.organization_email_handler import OrganizationEmailHandler
from models.auth_details import AuthDetails
from util.auth.auth_tool import authorize
from pydantic import BaseModel, Json
from datetime import datetime
from sqlalchemy import and_
import json
from types import SimpleNamespace

router = APIRouter(
    prefix="/organizations",
    tags=["organizations"],
    dependencies=[Depends(get_db_session), Depends(get_logger)]
)

DB = Annotated[Session, Depends(get_db_session)]
Logger = Annotated[LoggingService, Depends(get_logger)]
_fileHandler = Annotated[FileHandler, Depends(get_file_handler)]
OrganizationEmailer = Annotated[OrganizationEmailHandler, Depends(get_organization_email_handler)]

# Organization levels
# 0 - unapproved
# 1 - approved
# 2 - foundations

class OrganizationAddressDTO(BaseModel):
    region:str
    city:str
    brgy:str
    street:str
    zipcode:str
    coordinates:str

@router.get("/")
def retrieveOrganizations(db: DB, file_handler:_fileHandler, p: int = 1, c: int = 10):
    # also return images
    orgs:List[Organization] = db.query(Organization).filter(and_(Organization.is_active == True)).limit(c).offset((p-1)*c).all()
    to_return = []

    for org in orgs:
        profile_link = file_handler.get_org_profile(org.id)
        to_return.append({
            "id" : org.id,
            "owner_id" : org.owner_id,
            "name" : org.name,
            "description" : org.description,
            "tier" : org.tier,
            "created_at" : org.created_at,
            "profile_link" : profile_link[0] if profile_link[1] != False else None
        })

    return to_return

@router.get("/{id}")
def retrieveOrganization(db:DB, id:int, res: Response, file_handler:_fileHandler):
    org:Organization = db.query(Organization).filter(and_(Organization.id == id, Organization.is_deleted == False)).first()

    if org is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found."
        )
    
    profile_link = file_handler.get_org_profile(id)

    return {
        "id" : org.id,
        "owner_id" : org.owner_id,
        "name" : org.name,
        "description" : org.description,
        "tier" : org.tier,
        "created_at" : org.created_at,
        "profile_link" : profile_link
    }

class CreateOrganizationDTO(BaseModel):
    name:str
    description:str
    address: OrganizationAddressDTO

@router.post("/")
async def createOrganization(db:DB, res:Response, file_handler:_fileHandler, profile: UploadFile, organization_email_handler:OrganizationEmailer, body: Json = Form(), user: AuthDetails = Depends(get_current_user)):
    # check for authorization
    authorize(user,2,4)

    body:CreateOrganizationDTO = json.loads(json.dumps(body), object_hook=lambda d: SimpleNamespace(**d))

    # check if name already exists
    org:Organization = db.query(Organization).filter(Organization.name == body.name).first()

    if org is not None:
        res.status_code = 400
        return {"detail": "Name already exists"}

    org = Organization()

    org.name = body.name
    org.description = body.description
    org.owner_id = user.user_id
    org.tier = 0

    db.add(org)
    db.commit()

    #IDEA: return org id
    newAddress = Address()
    
    newAddress.owner_id = org.id
    newAddress.owner_type = "ORGANIZATION"
    newAddress.region = body.address.region
    newAddress.city = body.address.city
    newAddress.brgy = body.address.brgy
    newAddress.street = body.address.street
    newAddress.zipcode = body.address.zipcode
    newAddress.coordinates = body.address.coordinates

    db.add(newAddress)
    db.commit()

    resu = await file_handler.upload_file(profile, org.id, 'organizations')

    if resu[1] == False:
        print(f'Profile of organization {id} not added correctly.')

    user:User = db.query(User).filter(User.id == user.user_id).first()

    await organization_email_handler.send_organization_creation_notice(user.email, user.first_name, org.name)

    return {"details": "Organization created."}

@router.patch("/{id}/address")
def editOrganizationAddress(id:int, body:OrganizationAddressDTO, db:DB, res:Response, user: AuthDetails = Depends(get_current_user)):
    authorize(user, 2,5)
    
    org:Organization = db.query(Organization).filter(and_(Organization.id == id, Organization.is_deleted == False)).first()

    if org is None:
        res.status_code = 404
        return {"detail": "Organization non-existent"}
    
    if org.owner_id != user.user_id:
        res.status_code = 403
        return {"detail": "Forbidden access"}

    address:Address = db.query(Address).filter(Address.owner_type == 'ORGANIZATION' and Address.owner_id == id).first()

    if address is None:
        res.status_code = 404
        return {"detail": "No record of address from this organization"}

    address.region = address.region if body.region is "" else body.region
    address.city = address.city if body.city is "" else body.city
    address.brgy = address.brgy if body.brgy is "" else body.brgy
    address.street = address.street if body.street is "" else body.street
    address.zipcode = address.zipcode if body.zipcode is "" else body.zipcode
    address.coordinates = address.coordinates if body.coordinates is "" else body.coordinates
    address.updated_at = datetime.now()

    db.commit()
    
    return {"detail":"Organization success successfully updapted."}

@router.post("/{id}/profile")
async def saveOrganizationProfile(id: int, image: UploadFile, res: Response, db:DB, file_handler: _fileHandler, user: AuthDetails = Depends(get_current_user)):
    authorize(user, 2, 5)

    # get user id f rom authentication
    org:Organization = db.query(Organization).filter(and_(Organization.id == id, Organization.is_deleted == False)).first()

    if org is None:
        res.status_code = 404
        return {"detail" : "Organization not found"}

    if org.owner_id != user.user_id:
        res.status_code = 403
        return {"detail": "Forbidden action."}

    # check if file already exists
    if file_handler.file_exists(id, 'organizations') == True:
        # delete currently saved
        await file_handler.remove_file(id, 'organizations')
    
    # upload file
    await file_handler.upload_file(image, id, 'organizations')

    return {
        "detail": "Organization profile successfully uploaded."
    }

@router.get("/{id}/profile")
def retrieveOrganizationProfile(db:DB, id:int, res: Response, file_handler: _fileHandler):
    # check first if organization exists
    if db.query(Organization).filter(and_(Organization.id == id, Organization.is_deleted == False, Organization.is_active == True)).first() == None:
        res.status_code = 403
        return {'detail': 'Non-existent organization.'}

    profile_link = file_handler.get_org_profile(id)

    return profile_link

@router.get("/applications")
def retrieve_organization_applications(res:Response, db:DB, organization_email_handler:OrganizationEmailer, p: int = 1, c: int = 10, user: AuthDetails = Depends(get_current_user)):
    authorize(user, 4, 4)
    return db.query(Organization.tier).filter(and_(Organization.tier == 0, Organization.is_deleted == False)).limit(c).offset((p-1)*c).all()

@router.patch("/{org_id}/{action}")
async def resolve_organization_application(org_id:int, action:str, res:Response, db:DB, organization_email_handler:OrganizationEmailer, user: AuthDetails = Depends(get_current_user)):
    authorize(user, 4, 4) # only admins can access this

    org:Organization = db.query(Organization).filter(and_(Organization.id == org_id, Organization.is_deleted == False, Organization.is_active == False)).first()
    
    if org is None:
        res.status_code = 404
        return {'detail': 'Organization not found'}
    
    owner:User = db.query(User).filter(User.id == org.owner_id).first()
    
    match action.lower():
        case 'approve':
            org.tier = 1
            org.is_active = True
            if owner.level < 3:
                owner.level = 3 # signifies an organization owner
        case 'reject':
            org.is_deleted = True
        case _:
            res.status_code = 400
            return {'detail' : 'Invalid action'}
    
    org.updated_at = datetime.now()

    db.commit()

    # send email notification later

    return {'detail' : f'Successfully resolved organization with status: {action}'}

@router.delete("/{id}")
async def deleteOrganization(id:int, db:DB, res: Response, organization_email_handler:OrganizationEmailer, user: AuthDetails = Depends(get_current_user)):
    authorize(user, 3, 4)

    org:Organization = db.query(Organization).filter(and_(Organization.id == id, Organization.is_deleted == False)).first()
    
    if org is None:
        res.status_code = 404
        return {"detail": "Organization not found."}
    
    if org.owner_id is not user.user_id and user.level < 5:
        res.status_code = 403
        return {"detail": "Deletion not authorized."}

    org.is_deleted = True

    db.commit()

    user:User = db.query(User).filter(User.id == user.user_id).first()

    await organization_email_handler.send_deletion_notice(user.email, user.first_name, org.name)

    return {"detail": "Organization deleted"}

class SponsorshipRequestDTO(BaseModel):
    message: str
    organization_id: int
    foundation_id: int

@router.post("/sponsor")
def apply_for_sponsorship(body: SponsorshipRequestDTO, db:DB, res: Response, organization_email_handler:OrganizationEmailer, user: AuthDetails = Depends(get_current_user)):
    authorize(user,2,2)

    org:Organization = db.query(Organization).filter(and_(Organization.id == body.organization_id, Organization.is_deleted == False)).first()
    foundation:Organization = db.query(Organization).filter(and_(Organization.id == body.foundation_id, Organization.is_deleted == False, Organization.tier == 4)).first()

    if org is None:
        res.status_code = 400
        return {'detail' : 'Organization not found.'}
    
    if foundation is None:
        res.status_code = 400
        return {'detail' : 'Foundation not found.'}
    
    if org.owner_id != user.user_id:
        res.status_code = 403
        return {'detail' : 'Insufficient authorization to request for sponsorship.'}
    
    req:SponsorshipRequest = db.query(SponsorshipRequest).filter(and_(SponsorshipRequest.organization_id == body.organization_id, SponsorshipRequest.foundation_id == body.foundation_id, SponsorshipRequest.is_deleted == False)).first()

    if req is not None:
        res.status_code = 400
        return {'detail' : 'Request already exists'}
    
    req = SponsorshipRequest()
    
    req.organization_id = body.organization_id
    req.foundation_id = body.foundation_id
    req.message = body.message
    req.status = 'PENDING'

    db.add(req)
    db.commit()
    
    return {'detail' : 'Successfully sent sponsorship application request.'}