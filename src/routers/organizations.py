from typing import Annotated, List
from fastapi import APIRouter, Depends, UploadFile, HTTPException, status, Response, Body, Form
from dependencies import get_logger, get_current_user, get_organization_email_handler, get_file_handler
from services.db.database import Session
from services.db.models import Organization, User, Address, SponsorshipRequest
from services.storage.file_handler import FileHandler
from services.email.organization_email_handler import OrganizationEmailHandler
from models.auth_details import AuthDetails
from util.auth.auth_tool import authorize, is_authorized, is_user_organizer
from pydantic import BaseModel, Json
from datetime import datetime
from sqlalchemy import and_
import json
from types import SimpleNamespace

router = APIRouter(
    prefix="/organizations",
    tags=["organizations"],
    dependencies=[]
)

# _fileHandler = Annotated[FileHandler, Depends(get_file_handler)]
OrganizationEmailer = Annotated[OrganizationEmailHandler, Depends(get_organization_email_handler)]

db = Session()
file_handler = FileHandler()

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
async def retrieve_organizations(p: int = 1, c: int = 10):
    """
    Retrieves a paginated list of active organizations.
    """
    # Get list of active organizations from database
    orgs: List[Organization] = db.query(Organization).filter(and_(Organization.is_active == True)).limit(c).offset((p-1)*c).all()

    # Initialize empty list to store retrieved data
    to_return = []

    # Extract necessary data and generate profile links for each organization
    for org in orgs:
        profile_link = await file_handler.get_org_profile(org.id)
        to_return.append({
            "id": org.id,
            "owner_id": org.owner_id,
            "name": org.name,
            "description": org.description,
            "tier": org.tier,
            "created_at": org.created_at,
            "profile_link": profile_link
        })

    return to_return


@router.get("/{organization_id}")
async def retrieve_organization(organization_id: int, res: Response):
    """
    Retrieves details of an organization with the specified `organization_id`.
    """

    # Retrieve organization from database
    org: Organization = db.query(Organization).filter(and_(Organization.id == organization_id, Organization.is_deleted == False)).first()

    # Check if organization exists, raise 404 Not Found if not
    if org is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found."
        )

    # Get organization profile picture link
    profile_link = await file_handler.get_org_profile(organization_id)

    # Return organization details as a dictionary
    return {
        "id": org.id,
        "owner_id": org.owner_id,
        "name": org.name,
        "description": org.description,
        "tier": org.tier,
        "is_active": org.is_active,  # Include "is_active" field
        "created_at": org.created_at,
        "profile_link": profile_link
    }

class CreateOrganizationDTO(BaseModel):
    name:str
    description:str
    address: OrganizationAddressDTO

@router.post("/")
async def create_organization(res:Response, profile: UploadFile, organization_email_handler:OrganizationEmailer, body: Json = Form(), user: AuthDetails = Depends(get_current_user)):
    """
    Creates a new organization, uploads its profile picture, and sends a notification email.
    """

    # check for authorization
    authorize(user,2,4)

    # parses body data from request body
    body:CreateOrganizationDTO = json.loads(json.dumps(body), object_hook=lambda d: SimpleNamespace(**d))

    # check if name already exists
    org:Organization = db.query(Organization).filter(Organization.name == body.name).first()

    # check if org already exists. If true, return HTTP 400 indicating that the name is already taken.
    if org is not None:
        res.status_code = 400
        return {"detail": "Name already exists"}

    # initialize new organization
    org = Organization()

    # add relevant data
    org.name = body.name
    org.description = body.description
    org.owner_id = user.user_id
    org.tier = 0

    db.add(org)
    db.commit()

    # initializes organization address
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

    # upload organization profile
    resu = await file_handler.upload_file(profile, org.id, 'organizations')

    # notify in case profile is not added correctly
    if resu[1] == False:
        print(f'Profile of organization {id} not added correctly.')

    # get user info (for email)
    user:User = db.query(User).filter(User.id == user.user_id).first()

    # email user that an organization was creatd.
    await organization_email_handler.send_organization_creation_notice(user.email, user.first_name, org.name)

    return {"details": "Organization created."}

@router.patch("/{id}/address")
def edit_organization_address(id:int, body:OrganizationAddressDTO, res:Response, user: AuthDetails = Depends(get_current_user)):
    """
    Edits the address of an organization.
    """
    
    # checks for authorization
    authorize(user, 2,4)
    
    # retrieve organization
    org:Organization = db.query(Organization).filter(and_(Organization.id == id, Organization.is_deleted == False)).first()

    # checks if organization exists, returns HTTP 404 if not
    if org is None:
        res.status_code = 404
        return {"detail": "Organization non-existent"}
    
    # check if org owner is user
    if org.owner_id != user.user_id:
        res.status_code = 403
        return {"detail": "Forbidden access"}

    # retrieve address
    address:Address = db.query(Address).filter(Address.owner_type == 'ORGANIZATION' and Address.owner_id == id).first()
    
    address.region = address.region if body.region is "" else body.region
    address.city = address.city if body.city is "" else body.city
    address.brgy = address.brgy if body.brgy is "" else body.brgy
    address.street = address.street if body.street is "" else body.street
    address.zipcode = address.zipcode if body.zipcode is "" else body.zipcode
    address.coordinates = address.coordinates if body.coordinates is "" else body.coordinates
    address.updated_at = datetime.now()

    db.commit()
    
    return {"detail":"Organization success successfully updated."}

@router.post("/{organization_id}/profile")
async def save_organization_profile(organization_id: int, image: UploadFile, res: Response, user: AuthDetails = Depends(get_current_user)):
    """
    Saves a profile picture for an organization.
    """

    # checks user authorization
    authorize(user, 2, 4)

    # get user id f rom authentication
    org:Organization = db.query(Organization).filter(and_(Organization.id == organization_id, Organization.is_deleted == False)).first()

    # checks if org exists, returns HTTP 404 if not
    if org is None:
        res.status_code = 404
        return {"detail" : "Organization not found"}

    # checks if user is authorized to change profile, returns HTTP 403 if not
    if org.owner_id != user.user_id:
        res.status_code = 403
        return {"detail": "Forbidden action."}

    # check if file already exists
    if file_handler.file_exists(id, 'organizations') == True:
        # delete currently saved
        await file_handler.remove_file(organization_id, 'organizations')
    
    # upload organization profile
    await file_handler.upload_file(image, organization_id, 'organizations')

    return {
        "detail": "Organization profile successfully uploaded."
    }

@router.get("/{id}/profile")
def retrieve_organization_profile(id:int, res: Response):
    """
    Retrieves the profile picture link for an organization.
    """

    # check first if organization exists
    if db.query(Organization).filter(and_(Organization.id == id, Organization.is_deleted == False, Organization.is_active == True)).first() == None:
        res.status_code = 404
        return {'detail': 'Non-existent organization.'}

    # attains link
    profile_link = file_handler.get_org_profile(id)

    return profile_link

@router.get("/applications")
def retrieve_organization_applications(res:Response, organization_email_handler:OrganizationEmailer, p: int = 1, c: int = 10, user: AuthDetails = Depends(get_current_user)):
    """
    Retrieves a paginated list of applications from organizations requesting tier upgrade.
    """

    authorize(user, 4, 4) # only admins can access this

    # initialize array to return
    to_return = []

    orgs:List[Organization] = db.query(Organization.tier).filter(and_(Organization.tier == 0, Organization.is_deleted == False)).limit(c).offset((p-1)*c).all()

    # excludes unnecessary data
    for org in orgs:
        to_return.append({
            "id": org.id,
            "name" : org.name,
            "description" : org.description,
            "tier" : org.tier,
            "owner_id" : org.owner_id,
            "created_at" : org.created_at
            })
    
    # returns 
    return to_return

@router.patch("/{org_id}/{action}")
async def resolve_organization_application(org_id:int, action:str, res:Response, organization_email_handler:OrganizationEmailer, user: AuthDetails = Depends(get_current_user)):
    """
    Resolves organization application of `org_id` 
    """
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
async def deleteOrganization(id:int, res: Response, organization_email_handler:OrganizationEmailer, user: AuthDetails = Depends(get_current_user)):
    """
    Deletes an organization.
    """
    
    authorize(user, 3, 4)

    org:Organization = db.query(Organization).filter(and_(Organization.id == id, Organization.is_deleted == False)).first()
    
    # checks if organization exists
    if org is None:
        res.status_code = 404
        return {"detail": "Organization not found."}
    
    # checks if user is authorized to delete the organization
    if is_user_organizer(user, org.owner_id) == False:
        res.status_code = 403
        return {"detail": "Deletion not authorized."}

    # soft delete the organization
    org.is_deleted = True

    db.commit()

    user:User = db.query(User).filter(User.id == user.user_id).first()

    # send email to owner.
    await organization_email_handler.send_deletion_notice(user.email, user.first_name, org.name)

    return {"detail": "Organization deleted"}

class SponsorshipRequestDTO(BaseModel):
    message: str
    organization_id: int
    foundation_id: int

@router.post("/sponsor")
def apply_for_sponsorship(body: SponsorshipRequestDTO, res: Response, organization_email_handler:OrganizationEmailer, user: AuthDetails = Depends(get_current_user)):
    """
    Creates a sponsorship request for an organization to a foundation.
    """

    # check for user authentication
    authorize(user,2,3) # only users are allowed

    org:Organization = db.query(Organization).filter(and_(Organization.id == body.organization_id, Organization.is_deleted == False)).first()

    # checks if organization exists
    if org is None:
        res.status_code = 404
        return {'detail' : 'Organization not found.'}
    
    foundation:Organization = db.query(Organization).filter(and_(Organization.id == body.foundation_id, Organization.is_deleted == False, Organization.tier == 4)).first()

    # checks if foundation exists    
    if foundation is None:
        res.status_code = 404
        return {'detail' : 'Foundation not found.'}
    
    # checks if user is authorized to act behalf of org
    if org.owner_id != user.user_id:
        res.status_code = 403
        return {'detail' : 'Insufficient authorization to request for sponsorship.'}
    
    req:SponsorshipRequest = db.query(SponsorshipRequest).filter(and_(SponsorshipRequest.owner_id == body.organization_id, SponsorshipRequest.owner_type == 'ORGANIZATION', SponsorshipRequest.foundation_id == body.foundation_id, SponsorshipRequest.is_deleted == False)).first()

    # check if sponsorship request already exists
    if req is not None:
        res.status_code = 400
        return {'detail' : 'Request already exists'}
    
    req = SponsorshipRequest()
    
    req.owner_id = org.owner_id
    req.owner_type = 'ORGANIZATION'
    req.foundation_id = body.foundation_id
    req.message = body.message
    req.status = 'PENDING'

    db.add(req)
    db.commit()
    
    return {'detail' : 'Successfully sent sponsorship application request.'}