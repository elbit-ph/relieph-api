from typing import Annotated
from fastapi import APIRouter, Depends, UploadFile, HTTPException, status, Response, Body
from dependencies import get_db_session, get_logger, get_s3_handler, get_current_user
from services.db.database import Session
from services.db.models import Organization, User, Address
from services.log.log_handler import LoggingService
from services.aws.s3_handler import S3_Handler
from models.auth_details import AuthDetails
from util.auth.auth_tool import authorize
from pydantic import BaseModel
from datetime import datetime
from sqlalchemy import and_

router = APIRouter(
    prefix="/organizations",
    tags=["organizations"],
    dependencies=[Depends(get_db_session), Depends(get_logger)]
)

DB = Annotated[Session, Depends(get_db_session)]
Logger = Annotated[LoggingService, Depends(get_logger)]
S3Handler = Annotated[S3_Handler, Depends(get_s3_handler)]

@router.get("/")
def retrieveOrganizations(db: DB, p: int = 1, c: int = 10):
    return db.query(Organization).limit(c).offset((p-1)*c).all()

@router.get("/{id}")
def retrieveOrganization(db:DB, id:int):
    org:Organization = db.query(Organization).filter(and_(Organization.id == id, Organization.is_deleted == False)).first()

    if org is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found."
        )
    return org

class CreateOrganizationDTO(BaseModel):
    name:str
    description:str
    tier: int

@router.post("/")
def createOrganization(body: CreateOrganizationDTO, db:DB, res:Response, user: AuthDetails = Depends(get_current_user)):
    # check for authorization
    authorize(user,2,5)

    # check if name already exists
    org:Organization = db.query(Organization).filter(Organization.name == body.name).first()

    if org is not None:
        res.status_code = 400
        return {"detail": "Name already exists"}

    org = Organization()

    org.name = body.name
    org.description = body.description
    org.owner_id = user.user_id
    org.tier = body.tier

    db.add(org)
    db.commit()

    #IDEA: return org id
    org = db.query(Organization).filter(Organization.name == body.name).first()

    return {"details": "Organization created.",
            "org_id" : org.id}

class OrganizationAddressDTO(BaseModel):
    region:str
    city:str
    brgy:str
    street:str
    zipcode:str
    coordinates:str

@router.post("/{id}/address")
def addOrganizationAddress(id: int, body:OrganizationAddressDTO, db:DB, res:Response, user: AuthDetails = Depends(get_current_user)):
    authorize(user, 2,5)

    # catch if organization exists
    org:Organization = db.query(Organization).filter(and_(Organization.id == id, Organization.is_deleted == False)).first()

    if org is None:
        res.status_code = 404
        return {"detail": "Organization non-existent"}

    if org.owner_id != user.user_id:
        res.status_code = 403
        return {"detail": "Forbidden access"}

    address = Address()

    address.owner_id = user.user_id
    address.owner_type = 'ORGANIZATION'
    address.region = body.region
    address.city = body.city
    address.brgy = body.brgy
    address.street = body.street
    address.zipcode = body.zipcode
    address.coordinates = body.coordinates

    db.add(address)
    db.commit()
    
    return {"detail" : "Address added"}

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
    address.street = address.street if body.street is "" else body.street
    address.zipcode = address.zipcode if body.zipcode is "" else body.zipcode
    address.coordinates = address.coordinates if body.coordinates is "" else body.coordinates
    address.updated_at = datetime.now()

    db.commit()
    
    return {"detail":"Organization success successfully updapted."}

@router.post("/{id}/profile")
async def saveOrganizationProfile(id: int, image: UploadFile, res: Response, db:DB, s3:S3Handler, user: AuthDetails = Depends(get_current_user)):
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
    img = s3.get_image(id, 'users')
    if (img is None):
        # delete currently saved

        # temporarily return
        return

    await s3.upload_single_image(image, id, 'organizations')

    return {
        "detail": "Profile successfully uploaded."
    }

@router.get("/{id}/profile")
def retrieveOrganizationProfile(id:int, res: Response, s3: S3Handler):
    resu = s3.get_image(id, 'organizations')

    if resu[1] != True:
        res.status_code = 400
        return {'Error':'Invalid'}
     
    return {
        'link': resu[0]
    }

@router.post("/{id}/tier/{to}")
def changeTier(id:int, to:int, res:Response, db:DB, user: AuthDetails = Depends(get_current_user)):
    authorize(user, 5, 5)

    org:Organization = db.query(Organization).filter(and_(Organization.id == id, Organization.is_deleted == False)).first()

    if org is None:
        res.status_code = 404
        return {"details": "Organization not found."}

    org.tier = to

    db.commit()

    return {"detail":"Tier successfully changed"}

# to follow once foundation endpoints are created
# [POST] applyForSponsorship() - used to apply for foundation sponsorship

@router.delete("/{id}")
def deleteOrganization(id:int, db:DB, res: Response, user: AuthDetails = Depends(get_current_user)):
    authorize(user, 2, 5)

    org:Organization = db.query(Organization).filter(and_(Organization.id == id, Organization.is_deleted == False)).first()
    
    if org is None:
        res.status_code = 404
        return {"details": "Organization not found."}
    
    if org.owner_id is not user.user_id and user.level < 5:
        res.status_code = 403
        return {"detail": "Deletion not authorized."}

    org.is_deleted = True

    db.commit()

    return {"detail": "Organization deleted"}