from typing import Annotated
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status, Response, Form, Query
from dependencies import get_current_user
from services.db.database import Session, engine
from services.db.models import Organization, User, Address, ReliefEffort, ReliefBookmark, ReliefComment, InkindDonationRequirement, InkindDonation, VolunteerRequirement, ReliefUpdate
from services.storage.file_handler import FileHandler
from services.email.relief_email_handler import ReliefEmailHandler
from models.auth_details import AuthDetails
from util.auth.auth_tool import authorize, is_user_organizer, is_authorized
from util.files.image_validator import is_image_valid
from pydantic import BaseModel
from datetime import datetime, date
from sqlalchemy import and_, or_, text
from typing import List, Optional, Literal
from pydantic import Json, Field
import json
from types import SimpleNamespace
from sqlalchemy import Integer, Column
from enum import Enum

router = APIRouter(
    prefix="/reliefs",
    tags=["reliefs"],
    dependencies=[]
)

db = Session()
file_handler = FileHandler()
relief_email_handler = ReliefEmailHandler()

class ReliefEffortRetrievalDTO(BaseModel):
    keyword: str = ""
    category: str = "all"
    location: str = ""
    needs: List[str] = ['Monetary', 'Inkind', 'Volunteer Work']

valid_needs = ['Monetary', 'Inkind', 'Volunteer Work']

@router.get("/")
def retrieve_releief_efforts(keyword:str = "", category:str = "", location:str = "", needs:Annotated[list[str] | None, Query()] = ['Monetary', 'Inkind', 'Volunteer Work'], p: int = 1, c: int = 10):
    """
    Retrieves relief efforts. Paginated by count `c` and page `p`. Note: to submit multiple needs, do so by adding multiple `needs` query parameters.
    """
    print(needs)
    to_return = []
    
    detail_query = and_(ReliefEffort.is_active == True, ReliefEffort.disaster_type.contains(category), ReliefEffort.name.contains(keyword))
    
    address_query = None

    splitted_loc = location.split(', ')

    if len(splitted_loc) == 2:
        address_query = and_(Address.owner_id == ReliefEffort.id, Address.city == splitted_loc[0], Address.region == splitted_loc[1])
    else:
        address_query = and_(Address.owner_id == ReliefEffort.id)
    
    inkind_query = and_(InkindDonationRequirement.relief_id == ReliefEffort.id, InkindDonationRequirement.is_deleted == False)

    vol_query = and_(VolunteerRequirement.relief_id == ReliefEffort.id, VolunteerRequirement.is_deleted == False)

    if len(needs) < 3 or needs != valid_needs.sort():
        # some needs
        for i in range(0, len(needs)):
            needs[i] = needs[i].lower()

        match len(needs):
            case 1:
                match needs[0]:
                    case 'monetary':
                        # with monetary requirements
                        to_return = db.query(ReliefEffort, Address).filter(or_(ReliefEffort.monetary_goal > 0)).limit(c).offset((p-1)*c).all()
                    case 'inkind':
                        # with inkind requirements
                        to_return = db.query(ReliefEffort, Address).join(InkindDonationRequirement, InkindDonationRequirement.relief_id == ReliefEffort.id).filter(and_(detail_query, address_query, inkind_query)).limit(c).offset((p-1)*c).all()
                    case 'volunteer work':
                        # with volunteer requirements
                        to_return = db.query(ReliefEffort, Address).join(VolunteerRequirement, VolunteerRequirement.relief_id == ReliefEffort.id).filter(and_(detail_query, address_query, vol_query)).limit(c).offset((p-1)*c).all()
                    case _:
                        to_return = []
            case 2:
                needs.sort()
                match needs:
                    case ['inkind', 'monetary']:
                        # with inkind and monetary requirements
                        to_return = db.query(ReliefEffort, Address, InkindDonationRequirement).filter(and_(detail_query, address_query, inkind_query, ReliefEffort.monetary_goal > 0)).limit(c).offset((p-1)*c).all()
                    case ['monetary', 'volunteer work']:
                        # with monetary and volunteer requirements
                        to_return = db.query(ReliefEffort, Address, VolunteerRequirement).filter(and_(detail_query, address_query, vol_query, ReliefEffort.monetary_goal > 0)).limit(c).offset((p-1)*c).all()
                    case ['inkind', 'volunteer work']:
                        # with inkind and volunteer requirements
                        to_return = db.query(ReliefEffort, Address).filter(and_(detail_query, address_query, ReliefEffort.monetary_goal == 0)).limit(c).offset((p-1)*c).all()
                    case _:
                        to_return = []
            case _:
                # all
                to_return = db.query(ReliefEffort, Address).filter(and_(detail_query, address_query)).limit(c).offset((p-1)*c).all()
    else:
        to_return = db.query(ReliefEffort, Address).filter(and_(detail_query, address_query)).limit(c).offset((p-1)*c).all()
    
    return to_return

def get_inkind_requirements_total(relief_id:int):
    inkind_requirements = []

    with engine.connect() as con:
        rs = con.execute(f"SELECT \
                            idr.name,\
                            idr.description,\
                            idr.count AS target,\
                            idr.count - (SELECT COUNT(*) FROM inkind_donations id WHERE id.inkind_requirement_id = idr.id AND id.status = 'DELIVERED') AS count\
                            FROM inkind_donation_requirements idr\
                            WHERE idr.relief_id = {relief_id}")

        for row in rs:
            inkind_requirements.append({
                'name' : row[0],
                'description' : row[1],
                'target' : row[2],
                'count' : row[3]
            })

    return inkind_requirements

def get_inkind_total(relief_id:int):
    
    inkind_donations = []

    with engine.connect() as con:
        rs = con.execute(f"SELECT \
                            ink.quantity, \
                            ink.expiry, \
                            FROM inkind_donations ink \
                            WHERE ink.relief_id = {relief_id}")
        
    for row in rs:
        inkind_donations.append({
            'quantity': row[0],
            'expiry': row[1]
        })
    
    return inkind_donations

def get_volunteer_requirements_total(relief_id:int):

    volunteer_requirements = []

    with engine.connect() as con:
        rs = con.execute(f"SELECT \
                            vdr.name,\
                            vdr.description,\
                            vdr.count AS target,\
                            vdr.count - (SELECT COUNT(*) FROM volunteers vd WHERE vd.volunteer_requirement_id = vdr.id AND vd.status = 'ACCEPTED') AS count\
                            FROM volunteer_requirements vdr\
                            WHERE vdr.relief_id = {relief_id}")
        for row in rs:
            volunteer_requirements.append({
                'name' : row[0],
                'description' : row[1],
                'target' : row[2],
                'count' : row[3]
            })

    return volunteer_requirements

def get_comments_list(relief_id:int):

    comments_list = []

    with engine.connect() as con:
        rs = con.execute(f"SELECT \
                            cmt.user_id, \
                            cmt.message \
                            FROM relief_comments cmt \
                            WHERE cmt.relief_id = {relief_id} AND is_deleted = false")
        
        for row in rs:
            comments_list.append({
                'user_id' : row[0],
                'message' : row[1]
            })

        return comments_list

def get_updates_list(relief_id:int):

    updates_list = []

    with engine.connect() as con:
        rs = con.execute(f"SELECT \
                            upd.title, \
                            upd.description, \
                            upd.media_dir, \
                            upd.type \
                            FROM relief_updates upd \
                            WHERE upd.relief_id = {relief_id} AND is_deleted = false")
        
        for row in rs:
            updates_list.append({
                'title' : row[0],
                'description' : row[1],
                'media_dir' : row[2],
                'type' : row[3]
            })

        return updates_list

@router.get("/{relief_effort_id}")
async def retrieve_relief_effort(relief_effort_id:int):
    """
    Returns relief effort identified by `relief_effort_id`
    """
    relief:ReliefEffort = db.query(ReliefEffort).filter(ReliefEffort.id == relief_effort_id).first()

    # checks if relief effort exists
    if relief is None:
        raise HTTPException( 
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found."
        )

    resu = await file_handler.retrieve_files(relief_effort_id, f'relief-efforts/main')

    to_return = {
            'profile' : relief,
            'inkindDonations' : get_inkind_total(relief.id),
            'volunteerRequirements' : get_volunteer_requirements_total(relief.id),
            'comment_list' : get_comments_list(relief.id),
            'update_list' : get_updates_list(relief.id)
    }

    # retrieve monetary progress
    if resu[1] == True:
        to_return['images'] = resu[0]
    
    return to_return

class ReliefAddressDTO(BaseModel):
    region:str
    city:str
    brgy:str
    street:str
    zipcode:int
    coordinates:str

# inkind requirement: name, count
# volunteer reuqirement: name, count

class InkindRequirementDTO(BaseModel):
    name:str = Form()
    count:int = Form()

class VolunteerRequirementDTO(BaseModel):
    name:str
    count:int    

class CreateReliefEffortDTO(BaseModel):
    # basic info
    name: str # title
    description: str
    disaster_type: str
    # address
    address : ReliefAddressDTO
    # dates
    start_date: str
    deployment_date: str
    end_date: str
    # monetary goal & account details
    monetary_goal: float
    accountno: str
    platform: str

    inkind_requirements: List[InkindRequirementDTO] = None
    volunteer_requirements: List[VolunteerRequirementDTO] = None
    sponsor_message: str  = None

@router.post("/as-user")
async def create_relief_effort_as_individual(res: Response, body: CreateReliefEffortDTO, user: AuthDetails = Depends(get_current_user)):
    """
    Creates relief effort as a user.
    """
    authorize(user, 2, 4)
    
    # validate input
    body.start_date = date.fromisoformat(body.start_date)
    body.deployment_date = date.fromisoformat(body.deployment_date)
    body.end_date = date.fromisoformat(body.end_date)

    # validate dates
    if body.start_date < date.today() or body.end_date < date.today() or body.deployment_date < date.today():
        res.status_code = 400
        return {
            "detail" : "Invalid date input."
        }
    
    # check if all images are valid
    # for image in images:
    #     if is_image_valid(image) == False:
    #         return {"detail" : "One of uploaded files are invalid."}
        
    # save basic info
    relief:ReliefEffort = ReliefEffort()
    relief.owner_id = user.user_id
    relief.owner_type = 'USER'
    relief.name = body.name
    relief.description = body.description
    relief.disaster_type = body.disaster_type
    relief.monetary_goal = body.monetary_goal
    relief.account_number = body.accountno
    relief.money_platform = body.platform
    relief.start_date = body.start_date
    relief.deployment_date = body.deployment_date
    relief.end_date = body.end_date
    relief.phase = 'For Approval'

    db.add(relief)
    db.commit()
    
    # save images

    # upload pictures to their own folder
    # resu = await file_handler.upload_multiple_file(images, relief.id, f'relief-efforts/main')

    # if resu[1] == False:
    #     # do not terminate outright
    #     print(f'Images for relief id {relief.id} not uploaded.')
    
    # save address
    address = Address()
    address.owner_id = relief.id
    address.owner_type = 'RELIEF'
    address.region = body.address.region
    address.city = body.address.city
    address.brgy = body.address.brgy
    address.street = body.address.street
    address.zipcode = body.address.zipcode
    address.coordinates = body.address.coordinates

    db.add(address)
    db.commit()

    # save inkind requirements
    inkind_requirement_list = []

    for i_r in body.inkind_requirements:
        # generate 
        inkind_requirement = InkindDonationRequirement()
        inkind_requirement.name = i_r.name
        inkind_requirement.count = i_r.count
        inkind_requirement.relief_id = relief.id
        inkind_requirement_list.append(inkind_requirement)
    if len(inkind_requirement_list) > 0:
        db.add_all(inkind_requirement_list)
    
    # volunteer requirement
    # save volunteer requirements

    volunter_requirement_list = []

    for v_r in body.volunteer_requirements:
        volunteer_requirement = VolunteerRequirement()
        volunteer_requirement.name = v_r.name
        volunteer_requirement.count = v_r.count
        volunteer_requirement.relief_id = relief.id
        volunter_requirement_list.append(volunteer_requirement)

    if len(volunter_requirement_list) > 0:
        db.add_all(volunter_requirement_list)

    db.commit()

    return {
            "detail": "Relief effort successfully created",
            "data" : {
                "relief_id" : relief.id
            }}

@router.post("/as-organization/{organization_id}")
async def create_relief_effort_as_organization(res: Response, organization_id: int, body: CreateReliefEffortDTO, user: AuthDetails = Depends(get_current_user)):
    """
    Create relief effort as an organization.
    """

    authorize(user, 2, 4)
    
    # validate date input
    body.start_date = date.fromisoformat(body.start_date)
    body.deployment_date = date.fromisoformat(body.deployment_date)
    body.end_date = date.fromisoformat(body.end_date)

    org: Organization = db.query(Organization).filter(and_(Organization.id == organization_id, Organization.is_deleted == False, Organization.is_active == True)).first()

    # if org is not found, return HTTP 404
    if org is None:
        res.status_code = 404
        return {"detail": "Organization not found."}
    
    # check if user is authorized to act on behalf of organization
    if org.owner_id != user.user_id:
        res.status_code = 403
        return {"detail": "Not authorized to create relief effort."}

    # validate date input
    if body.start_date < date.today() or body.end_date < date.today() or body.deployment_date < date.today():
        res.status_code = 400
        return {
            "detail" : "Invalid date input."
        }
    
    relief:ReliefEffort = ReliefEffort()
    relief.owner_id = organization_id
    relief.owner_type = 'ORGANIZATION'
    relief.name = body.name
    relief.description = body.description
    relief.disaster_type = body.disaster_type
    relief.monetary_goal = body.monetary_goal
    relief.account_number = body.accountno
    relief.money_platform = body.platform
    relief.start_date = body.start_date
    relief.deployment_date = body.deployment_date
    relief.end_date = body.end_date
    relief.phase = 'For Approval'

    db.add(relief)
    db.commit()
    
    # save address
    address = Address()
    address.owner_id = relief.id
    address.owner_type = 'RELIEF'
    address.region = body.address.region
    address.city = body.address.city
    address.brgy = body.address.brgy
    address.street = body.address.street
    address.zipcode = body.address.zipcode
    address.coordinates = body.address.coordinates

    db.add(address)
    db.commit()

    # save inkind requirements
    inkind_requirement_list = []

    for i_r in body.inkind_requirements:
        # generate 
        inkind_requirement = InkindDonationRequirement()
        inkind_requirement.name = i_r.name
        inkind_requirement.count = i_r.count
        inkind_requirement.relief_id = relief.id
        inkind_requirement_list.append(inkind_requirement)

    if inkind_requirement_list.count() > 0:
        db.add_all(inkind_requirement_list)

    # save volunteer requirements
    volunter_requirement_list = []

    for v_r in body.volunteer_requirements:
        volunteer_requirement = VolunteerRequirement()
        volunteer_requirement.name = v_r.name
        volunteer_requirement.count = v_r.count
        volunteer_requirement.relief_id = relief.id
        volunter_requirement_list.append(volunteer_requirement)
    
    if volunter_requirement_list.count() > 0:
        db.add_all(volunter_requirement_list)

    if org.tier > 1:
        # automatically set relief to active if org tier
        # is greater than 1
        relief.is_active = True
    else:
        relief.phase = 'For Approval'

    db.add(relief)
    db.commit()

    return {"detail": "Relief effort successfully created", 
            "data" : {
                "organization_id" : organization_id
            }}

@router.post("/{relief_id}/images")
async def upload_relief_images(relief_id:int, res:Response, images:List[UploadFile] = File(...), user:AuthDetails = Depends(get_current_user)):
    # check if images are valid
    for image in images:
        if is_image_valid(image) == False:
            res.status_code = 404
            return {'detail' : 'Invalid image type in one or more images uploaded.'}
    
    relief_effort:ReliefEffort = db.query(ReliefEffort).filter(and_(ReliefEffort.id == relief_id, ReliefEffort.is_deleted == False)).first()

    # check if relief effort exists
    if relief_effort is None:
        res.status_code = 404
        return {'detail' : 'Relief effort not found.'}
    
    # check if user can act on behalf of relief effort
    if is_authorized(relief_effort.owner_id, relief_effort.owner_type, user) == False:
        res.status_code = 403
        return {'detail': 'Not authorized to affect on behalf of relief effort.'}

    # upload images
    resu = await file_handler.upload_multiple_file(images, relief_id, 'relief-efforts/main')

    # check if upload was successful
    if resu[1] == False:
        res.status_code = 500
        return {'detail' : 'Unable to upload images.'}
    
    return {'detail' : 'Images uploaded.'}

@router.patch("/{id}/approve")
async def approveReliefEffort(id:int, res: Response, user: AuthDetails = Depends(get_current_user)):
    """
    Approves a relief effort.
    """

    authorize(user, 2, 4)

    # TO FOLLOW: allow foundations to approve relief efforts so long
    # as organization is sponsored/supported by said foundation

    relief:ReliefEffort = db.query(ReliefEffort).filter(and_(ReliefEffort.id == id, ReliefEffort.is_active == False, ReliefEffort.is_deleted == False)).first()

    # checks if relief effort is found
    if relief is None:
        res.status_code = 404
        return {"detail": "Relief effort non-existent."}
    
    usr:User = None
    
    # checks if relief effort is owned by organization
    if relief.owner_type == 'ORGANIZATION':
        org:Organization = db.query(Organization).filter(and_(Organization.id == relief.owner_id)).first()
        foundation:Organization = db.query(Organization).filter(and_(Organization.id == org.sponsor_id)).first()
        # checks if user is either admin or foundation
        if user.level != 4 and (foundation is None or user.user_id != foundation.owner_id):
            res.status_code = 403
            return {'detail' : 'Not authorized'}
        # get user affliated
        usr = db.query(User).join(Organization).filter(and_(Organization.owner_id == User.id, Organization.id == relief.owner_id)).first()
    else:
        # get user straight
        usr = db.query(User).filter(User.id == relief.owner_id).first()

    email = usr.email
    name = usr.first_name

    # send email notification about approval
    await relief_email_handler.send_approval(email, name, relief.name)
    
    relief.is_active = True
    relief.phase = 'PREPARING'
    relief.updated_at = datetime.now()

    db.commit()
    
    return {"detail": "Relief effort successfully approved"}

@router.patch("/{id}/reject")
async def rejectReliefEffort(id:int, res: Response,user: AuthDetails = Depends(get_current_user)):
    """
    Rejects a relief effort
    """
    authorize(user, 4, 4)

    # TO FOLLOW: allow foundations to reject relief efforts so long
    # as organization is sponsored/supported by said foundation

    relief:ReliefEffort = db.query(ReliefEffort).filter(and_(ReliefEffort.id == id, ReliefEffort.is_deleted == False)).first()

    # checks if relief is not found
    if relief is None:
        res.status_code = 404
        return {"detail": "Relief effort non-existent."}
    
    relief.is_deleted = True
    relief.is_active = False
    relief.phase = 'REJECTED'
    relief.updated_at = datetime.now()

    usr:User = None

    if relief.owner_type == 'ORGANIZATION':
        # get user affliated
        org:Organization = db.query(Organization).filter(and_(Organization.id == relief.owner_id)).first()
        foundation:Organization = db.query(Organization).filter(and_(Organization.id == org.sponsor_id)).first()

        # checks if user is either admin or attributed foundation
        if user.level != 4 and (foundation is None or user.user_id != foundation.owner_id):
            res.status_code = 403
            return {'detail' : 'Not authorized'}
        
        usr = db.query(User).join(Organization).filter(and_(Organization.owner_id == User.id, Organization.id == relief.owner_id)).first()
    else:
        # get user straight
        usr = db.query(User).filter(User.id == relief.owner_id).first()

    email = usr.email
    name = usr.first_name

    # send email about this
    await relief_email_handler.send_rejection(email, name, relief.name)

    db.commit()

    return {"detail": "Relief effort successfully rejected."}

@router.delete("/{id}")
async def delete_relief_effort(id:int, res: Response,user: AuthDetails = Depends(get_current_user)):
    """
    Deletes a relief effort.
    """
    authorize(user, 4, 4) # only admins can take down relief efforts

    relief:ReliefEffort = db.query(ReliefEffort).filter(and_(ReliefEffort.id == id, ReliefEffort.is_deleted == False)).first()
    
    # checks if relief effort exists
    if relief is None:
        res.status_code = 404
        return {"detail": "Relief effort non-existent."}
    
    relief.is_deleted = True
    relief.is_active = False
    relief.phase = 'Deleted'
    relief.updated_at = datetime.now()

    # send email about this
    user:User = None

    if relief.owner_type == 'ORGANIZATION':
        # get user affliated
        user = db.query(User).join(Organization).filter(and_(Organization.owner_id == User.id, Organization.id == relief.owner_id)).first()
    else:
        # get user straight
        user = db.query(User).filter(User.id == relief.owner_id).first()

    email = user.email
    name = user.first_name

    # send email about this
    await relief_email_handler.send_deletion_notice(email, name, relief.name)

    db.commit()

    return {"detail": "Relief effort successfully deleted."}

@router.get("/bookmarks/")
def retrieve_book_marks(res:Response, user: AuthDetails = Depends(get_current_user)):
    """
    Retrieves bookmarks of user
    """

    authorize(user, 1, 4)
    
    bookmarks = db.query(ReliefBookmark).filter(and_(ReliefBookmark.user_id == user.user_id)).all()

    return bookmarks

@router.post("/bookmarks/{id}")
def bookmark_relief_effort(id:int, res:Response, user: AuthDetails = Depends(get_current_user)):
    """
    Creates bookmark
    """
    authorize(user, 1, 4)

    relief: ReliefEffort = db.query(ReliefEffort).filter(and_(ReliefEffort.id == id, ReliefEffort.is_active == True)).first()

    if relief is None:
        res.status_code = 404
        return {"detail": "Relief effort non-existent"}
    
    bookmark:ReliefBookmark = db.query(ReliefBookmark).filter(and_(ReliefBookmark.user_id == user.user_id, ReliefBookmark.relief_id == id)).first()

    if bookmark is not None:
        res.status_code = 300
        return {"detail" : "Bookmark already exists."}
    
    # create new
    bookmark = ReliefBookmark()
    bookmark.user_id = user.user_id
    bookmark.relief_id = id
    db.add(bookmark)
    db.commit()

    # add relief effort to user's bookmarks
    return {"detail": "Relief effort bookmarked"}

@router.delete("/bookmarks/{id}")
def unbookmark_relief_effort(id:int, res:Response, user: AuthDetails = Depends(get_current_user)):
    """
    Removes bookmark
    """
    authorize(user, 1, 4)
    
    bookmark:ReliefBookmark = db.query(ReliefBookmark).filter(and_(ReliefBookmark.user_id == user.user_id, ReliefBookmark.relief_id == id)).first()

    if bookmark is None:
        res.status_code = 404
        return {"detail" : "Bookmark non-existent."}
    
    db.delete(bookmark)

    db.commit()

    return {"detail": "Relief effort unbookmarked"}

@router.get("/{id}/comments")
def get_comments(id:int, res:Response):
    """
    Retrieves comments of a relief effort
    """
    comments = db.query(ReliefComment).filter(ReliefComment.id == id).all()
    return comments

class ReliefCommentDTO(BaseModel):
    message: str

@router.post("/{id}/comments")
def create_comment(id:int, body: ReliefCommentDTO, res:Response, user: AuthDetails = Depends(get_current_user)):
    """
    Creates comment
    """
    
    # checks if user is authorized
    authorize(user, 1, 4)

    # checks if message is not present
    if body.message == None or body.message == "":
        res.status_code = 400
        return {"detail": "Blank message"}
    
    # check if relief exists
    relief: ReliefEffort = db.query(ReliefEffort).filter(and_(ReliefEffort.id == id, ReliefEffort.is_deleted == False)).first()
    
    if relief is None:
        res.status_code = 404
        return {"detail" : "Relief effort not found"}
    
    comment = ReliefComment()
    comment.message = body.message
    comment.relief_id = id
    comment.user_id = user.user_id

    db.add(comment)
    db.commit()

    return {"detail": "Sucessfully created comment"}

@router.delete("/{id}/comments/{comment_id}")
def delete_comment(id:int, comment_id:int, res:Response, user: AuthDetails = Depends(get_current_user)):
    """
    Deletes comment
    """

    # checks if user is authorized
    authorize(user, 2, 4)

    comment:ReliefComment = db.query(ReliefComment).filter(and_(ReliefComment.relief_id == id, ReliefComment.id == comment_id, ReliefComment.is_deleted == False)).first()

    # checks if comment exists
    if comment is None:
        res.status_code = 404
        return {"detail" : "Comment not found"}
    
    # checks if user is admin or is the commenter
    if user.level != 4 and user.user_id != comment.user_id:
        res.status_code = 403
        return {"detail" : "Forbidden deletion"}
    
    # mark comment as deleted
    comment.is_deleted = True

    db.commit()

    return {"detail": "Sucessfully deleted comment"}

@router.get("/{id}/updates")
def retrieve_updates(id:int, f: str = None):
    """
    Retrieves updates of relief effort with `id`
    """
    
    #updates:List[ReliefUpdate] = db.query(ReliefUpdate).filter(and_(ReliefUpdate.relief_id == id, ReliefUpdate.is_deleted == False))
    updates:List[ReliefUpdate] = List[ReliefUpdate]
    
    # apply filter `f`
    if f is not None:
        # also check if filter is valid here
        updates = db.query(ReliefUpdate).filter(and_(ReliefUpdate.relief_id == id, ReliefUpdate.is_deleted == False, ReliefUpdate.type == f)).all()
    else:
        # for none and/or invalid filters
        updates = db.query(ReliefUpdate).filter(and_(ReliefUpdate.relief_id == id, ReliefUpdate.is_deleted == False)).all()
        
    # apply filter later
    return updates

@router.get("/{id}/updates/{update_id}/images")
async def retrieve_update_images(id:int, res:Response, update_id:int):
    """
    Retrieve images of update `update_id` of relief `id`
    """

    # get image
    resu = await file_handler.retrieve_files(id, f'relief-efforts/{id}/updates/{update_id}')

    if resu[1] == False:
        res.status_code = 404
        return {"detail" : "Images not found."}

    return resu[0]

class CreateUpdateDTO(BaseModel):
    owner_type: str # ORGANIZATION || USER
    owner_id: int
    title: str
    message: str
    type: str = None

@router.post("/{id}/updates")
async def create_update(id:int, res:Response, body: CreateUpdateDTO, user: AuthDetails = Depends(get_current_user)):
    """
    Create update for relief `id`
    """

    authorize(user, 2, 4)
    
    # check if relief exists
    relief:ReliefEffort = db.query(ReliefEffort).filter(and_(ReliefEffort.id == id, ReliefEffort.is_active == False)).first()

    # checks if relief exists
    if relief is None:
        res.status_code = 404
        return {"detail" : "Relief effort not found."}

    # check if owner_id is authorized to act for the relief effort
    if relief.owner_id != body.owner_id:
        res.status_code = 403
        return {"detail" : "Not authorized to create an update. Trying logging in."}
    
    # check authorization depending on owner type
    match body.owner_type:
        case 'USER':
            if relief.owner_id != user.user_id:
                # checks if current user is owner of relief effort
                if org.owner_id != user.user_id:
                    res.status_code = 403
                    return {"detail" : "Not authorized to create an update. Log in with authorized user."}
        case 'ORGANIZATION':
            # check if user is authorized to act for the organization
            org:Organization = db.query(Organization).filter(and_(Organization.id == relief.owner_id, Organization.is_active == True)).first()
            # checks if organization exists
            if org is None:
                res.status_code = 401
                return {"detail" : "Organization not found"}
            # checks if current user is org owner
            if org.owner_id != user.user_id:
                res.status_code = 403
                return {"detail" : "Not authorized to create an update. Log in with authorized user."}
        case _:
            # invalid owner type
            res.status_code = 400
            return {"detail" : "Invalid owner type"}
    
    # instantiate relief effort
    update: ReliefUpdate = ReliefUpdate()

    update.title = body.title
    update.description = body.message
    update.relief_id = id
    update.type = body.type if hasattr(body, 'type') else 'General'

    db.add(update)
    db.commit()

    return {"detail": "Successfully created update.",
            "data" : {
                "relief_id" : relief.id,
                "update_id" : update.id
            }}

@router.post('/{relief_id}/updates/{update_id}')
async def upload_update_images(update_id:int, relief_id:int, res:Response, images:List[UploadFile] = File(...), user: AuthDetails = Depends(get_current_user)):
    authorize(user, 2, 4)

    # check if images are valid
    for image in images:
        if is_image_valid(image) == False:
            res.status_code = 400
            return {'detail' : 'One or more of the images uploaded have invalid file formats.'}
    
    relief_effort:ReliefEffort = db.query(ReliefEffort).filter(and_(ReliefEffort.id == relief_id, ReliefEffort.is_deleted == False)).first()

    # check if relief exists    
    if relief_effort is None:
        res.status_code = 404
        return {'detail' : 'Relief effort non-existent'}
    
    relief_update = db.query(ReliefUpdate).filter(and_(ReliefUpdate.id == update_id, ReliefUpdate.is_deleted == False)).first()

    # check if update exists
    if relief_update is None:
        res.status_code = 404
        return {'detail': 'Relief update non-existing'}

    # check if user is authorized to act on behalf
    if is_authorized(relief_effort.owner_id, relief_effort.owner_type, user) == False:
        res.status_code = 403
        return {'detail' : 'Unable to act on behalf of relief effort.'}
    
    # add images
    resu = await file_handler.upload_multiple_file(images, update_id, 'relief-efforts/updates')

    if resu[1] == False:
        res.status_code = 500
        return {'detail' : 'Unable to upload images'}
    
    return {'detail': 'Successfully uploaded images to relief update.'} 

class ReliefUpdateStatusDTO(BaseModel):
    owner_type: str
    owner_id: int
    phase: str

@router.patch("/{id}/phase")
async def update_relief_phase(id:int, res:Response, body: ReliefUpdateStatusDTO, user: AuthDetails = Depends(get_current_user)):
    """
    Manually update relief effort's phase.
    """
    authorize(user, 2, 4)
    
    # check if relief exists
    relief:ReliefEffort = db.query(ReliefEffort).filter(and_(ReliefEffort.id == id, ReliefEffort.is_active == True)).first()

    if relief is None:
        res.status_code = 404
        return {"detail" : "Relief effort not found."}

    # check if owner_id is authorized to act for the relief effort
    if relief.owner_id != body.owner_id:
        res.status_code = 403
        return {"detail" : "Not authorized to create an update. Trying logging in."}
    
    match body.owner_type:
        case 'USER':
            if relief.owner_id != user.user_id:
                if org.owner_id != user.user_id:
                    res.status_code = 403
                    return {"detail" : "Not authorized to create an update. Log in with authorized user."}
        case 'ORGANIZATION':
            # check if user is authorized to act for the organization
            org:Organization = db.query(Organization).filter(and_(Organization.id == relief.owner_id, Organization.is_active == True)).first()
            if org is None:
                res.status_code = 401
                return {"detail" : "Organization not found"}
            if org.owner_id != user.user_id:
                res.status_code = 403
                return {"detail" : "Not authorized to create an update. Log in with authorized user."}
        case _:
            # invalid owner type
            res.status_code = 400
            return {"detail" : "Invalid owner type"}
    
    # check if phase is valid
    if body.phase not in ('Preparing', 'Deployment', 'Completed'):
        res.status_code = 400
        return {"detail" : "Invalid phase."}

    # update status
    relief.phase = body.phase
    relief.updated_at = datetime.now()
    db.commit()

    return {"detail" : "Relief effort phase updated."}