from typing import Annotated
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status, Response, Form
from dependencies import get_db_session, get_logger, get_current_user, get_relief_email_handler, get_file_handler
from services.db.database import Session
from services.db.models import Organization, User, Address, ReliefEffort, ReliefBookmark, ReliefComment, InkindDonationRequirement, VolunteerRequirement, ReliefUpdate
from services.log.log_handler import LoggingService
from services.storage.file_handler import FileHandler
from services.email.relief_email_handler import ReliefEmailHandler
from models.auth_details import AuthDetails
from util.auth.auth_tool import authorize
from util.files.image_validator import is_image_valid
from pydantic import BaseModel
from datetime import datetime, date
from sqlalchemy import and_, or_
from typing import List
from pydantic import Json
import json
from types import SimpleNamespace

router = APIRouter(
    prefix="/reliefs",
    tags=["reliefs"],
    dependencies=[Depends(get_db_session), Depends(get_logger)]
)

DB = Annotated[Session, Depends(get_db_session)]
Logger = Annotated[LoggingService, Depends(get_logger)]
_fileHandler = Annotated[FileHandler, Depends(get_file_handler)]
ReliefEmail = Annotated[ReliefEmailHandler, Depends(get_relief_email_handler)]

class ReliefEffortRetrievalDTO(BaseModel):
    keyword: str = ""
    category: str = "all"
    location: str = ""
    needs: List[str] = ['Monetary', 'Inkind', 'Volunteer Work']

valid_needs = ['Monetary', 'Inkind', 'Volunteer Work']

@router.get("/")
def retrieveReliefEfforts(db: DB, body:ReliefEffortRetrievalDTO, p: int = 1, c: int = 10):
    to_return = []
    
    detail_query = and_(ReliefEffort.is_active == True, ReliefEffort.disaster_type.contains(body.category), ReliefEffort.name.contains(body.keyword))
    
    address_query = None

    splitted_loc = body.location.split(', ')

    if len(splitted_loc) == 2:
        address_query = and_(Address.owner_id == ReliefEffort.id, Address.city == splitted_loc[0], Address.region == splitted_loc[1])
    else:
        address_query = and_(Address.owner_id == ReliefEffort.id)
    
    inkind_query = and_(InkindDonationRequirement.relief_id == ReliefEffort.id, InkindDonationRequirement.is_deleted == False)

    vol_query = and_(VolunteerRequirement.relief_id == ReliefEffort.id, VolunteerRequirement.is_deleted == False)

    if len(body.needs) < 3 or body.needs != valid_needs.sort():
        # some needs
        for i in range(0, len(body.needs)):
            body.needs[i] = body.needs[i].lower()

        match len(body.needs):
            case 1:
                match body.needs[0]:
                    case 'monetary':
                        to_return = db.query(ReliefEffort, Address).filter(or_(ReliefEffort.monetary_goal > 0)).limit(c).offset((p-1)*c).all()
                    case 'inkind':
                        to_return = db.query(ReliefEffort, Address).join(InkindDonationRequirement, InkindDonationRequirement.relief_id == ReliefEffort.id).filter(and_(detail_query, address_query, inkind_query)).limit(c).offset((p-1)*c).all()
                    case 'volunteer work':
                        to_return = db.query(ReliefEffort, Address).join(VolunteerRequirement, VolunteerRequirement.relief_id == ReliefEffort.id).filter(and_(detail_query, address_query, vol_query)).limit(c).offset((p-1)*c).all()
                    case _:
                        to_return = []
            case 2:
                body.needs.sort()
                match body.needs:
                    case ['inkind', 'monetary']:
                        to_return = db.query(ReliefEffort, Address, InkindDonationRequirement).filter(and_(detail_query, address_query, inkind_query, ReliefEffort.monetary_goal > 0)).limit(c).offset((p-1)*c).all()
                    case ['monetary', 'volunteer work']:
                        to_return = db.query(ReliefEffort, Address, VolunteerRequirement).filter(and_(detail_query, address_query, vol_query, ReliefEffort.monetary_goal > 0)).limit(c).offset((p-1)*c).all()
                    case ['inkind', 'volunteer work']:
                        to_return = db.query(ReliefEffort, Address).filter(and_(detail_query, address_query, ReliefEffort.monetary_goal == 0)).limit(c).offset((p-1)*c).all()
                    case _:
                        to_return = []
            case _:
                # all
                to_return = db.query(ReliefEffort, Address).filter(and_(detail_query, address_query)).limit(c).offset((p-1)*c).all()
    else:
        to_return = db.query(ReliefEffort, Address).filter(and_(detail_query, address_query)).limit(c).offset((p-1)*c).all()
    
    return to_return

@router.get("/{id}")
def retrieveReliefEffort(db:DB, id:int):
    relief:ReliefEffort = db.query(ReliefEffort).filter(ReliefEffort.id == id).first()

    if relief is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found."
        )
    
    return relief

class ReliefAddressDTO(BaseModel):
    region:str
    city:str
    brgy:str
    street:str
    zipcode:int
    coordinates:str

class CreateReliefEffortDTO(BaseModel):
    # basic info
    name: str # title
    description: str
    disaster_type: str
    # address
    address:ReliefAddressDTO
    # dates
    start_date: date
    end_date: date
    # monetary goal & account details
    monetary_goal: float
    accountno: str
    platform: str
    inkind_requirements: list
    volunteer_requirements: list # object list {type, slots, duration}
    sponsor_message: str = None

# @router.get("/{id}/images")
# async def test(db:DB, id:int, file_handler:_fileHandler, res: Response):
#     resu = await file_handler.retrieve_files(id, f'relief-efforts/{id}/main')
#     if resu[0] is "ImagesNonExistent":
#         res.status_code = 404
#         return {"detail" : "Relief images non-existent."}
#     if resu[0] is "ErrorPresigning":
#         res.status_code = 500
#         return {"detail" : "Error generating images' urls"}
#     return resu[0]

@router.post("/user")
async def createReliefEffortAsIndividual(db:DB, file_handler:_fileHandler, res: Response, body: Json = Form(), images:List[UploadFile] = File(...) ,user: AuthDetails = Depends(get_current_user)):
    authorize(user, 2, 4)
    
    # IDEA: check how many relief effort an individual first has
    # limit the amount of relief effort an indivdual can create
    body:CreateReliefEffortDTO = json.loads(json.dumps(body), object_hook=lambda d: SimpleNamespace(**d))
    
    # validate input
    body.start_date = date.fromisoformat(body.start_date)
    body.end_date = date.fromisoformat(body.end_date)

    if body.start_date < date.today() or body.end_date < date.today():
        res.status_code = 400
        return {
            "detail" : "Invalid date input."
        }
    
    for image in images:
        if is_image_valid(image) == False:
            return {"detail" : "One of uploaded files are invalid."}
        
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
    relief.end_date = body.end_date
    relief.phase = 'For Approval'

    db.add(relief)
    db.commit()
    
    # save images

    resu = await file_handler.upload_multiple_file(images, relief.id, f'relief-efforts/{relief.id}/main')

    if resu[1] == False:
        # do not terminate outright
        print(f'Images for relief id {relief.id} not uploaded.')
    
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

    db.add_all(inkind_requirement_list)
    db.commit()

    # save volunteer requirements

    volunter_requirement_list = []

    for v_r in body.volunteer_requirements:
        volunteer_requirement = VolunteerRequirement()
        volunteer_requirement.name = v_r.name
        volunteer_requirement.count = v_r.count
        volunteer_requirement.relief_id = relief.id
        volunter_requirement_list.append(volunteer_requirement)
    
    db.add_all(volunter_requirement_list)
    db.commit()

    return {"detail": "Relief effort successfully created"}

@router.post("/organization/{id}")
async def createReliefEffortAsOrganization(db:DB, file_handler:_fileHandler, res: Response, id: int, body: Json = Form(), images:List[UploadFile] = File(...) ,user: AuthDetails = Depends(get_current_user)):
    authorize(user, 2, 4)

    # IDEA: check how many relief effort an individual first has
    # limit the amount of relief effort an indivdual can create

    body:CreateReliefEffortDTO = json.loads(json.dumps(body), object_hook=lambda d: SimpleNamespace(**d))
    
    # validate input
    body.start_date = date.fromisoformat(body.start_date)
    body.end_date = date.fromisoformat(body.end_date)

    org: Organization = db.query(Organization).filter(and_(Organization.id == id, Organization.is_deleted == False, Organization.is_active == True)).first()

    if org is None:
        res.status_code = 404
        return {"detail": "Organization not found."}
    
    if org.owner_id != user.user_id:
        res.status_code = 403
        return {"detail": "Not authorized to create relief effort."}

    # validate input
    if body.start_date < date.today() or body.end_date < date.today():
        res.status_code = 400
        return {
            "detail" : "Invalid date input."
        }
    
    for image in images:
        if is_image_valid(image) == False:
            return {"detail" : "One of uploaded files are invalid."}
    
    relief:ReliefEffort = ReliefEffort()
    relief.owner_id = id
    relief.owner_type = 'ORGANIZATION'
    relief.name = body.name
    relief.description = body.description
    relief.disaster_type = body.disaster_type
    relief.monetary_goal = body.monetary_goal
    relief.account_number = body.accountno
    relief.money_platform = body.platform
    relief.start_date = body.start_date
    relief.end_date = body.end_date
    relief.phase = 'For Approval'

    db.add(relief)
    db.commit()

    resu = await file_handler.upload_multiple_file(images, relief.id, f'relief-efforts/{relief.id}/main')

    if resu[1] == False:
        # do not terminate outright
        print(f'Images for relief id {relief.id} not uploaded.')
    
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

    db.add_all(inkind_requirement_list)
    db.commit()

    # save volunteer requirements
    volunter_requirement_list = []

    for v_r in body.volunteer_requirements:
        volunteer_requirement = VolunteerRequirement()
        volunteer_requirement.name = v_r.name
        volunteer_requirement.count = v_r.count
        volunteer_requirement.relief_id = relief.id
        volunter_requirement_list.append(volunteer_requirement)
    
    db.add_all(volunter_requirement_list)
    db.commit()

    if org.tier > 1:
        # automatically set relief to active if org tier
        # is greater than 1
        relief.is_active = True
    else:
        relief.phase = 'For Approval'

    db.add(relief)
    db.commit()

    return {"detail": "Relief effort successfully created"}

@router.patch("/approve/{id}")
async def approveReliefEffort(db:DB, id:int, res: Response, relief_email_handler: ReliefEmail, user: AuthDetails = Depends(get_current_user)):
    authorize(user, 2, 4)

    # TO FOLLOW: allow foundations to approve relief efforts so long
    # as organization is sponsored/supported by said foundation

    relief:ReliefEffort = db.query(ReliefEffort).filter(and_(ReliefEffort.id == id, ReliefEffort.is_active == False, ReliefEffort.is_deleted == False)).first()

    if relief is None:
        res.status_code = 404
        return {"detail": "Relief effort non-existent."}
    
    usr:User = None

    if relief.owner_type == 'ORGANIZATION':
        org:Organization = db.query(Organization).filter(and_(Organization.id == relief.owner_id)).first()
        foundation:Organization = db.query(Organization).filter(and_(Organization.id == org.sponsor_id)).first()

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

    # send email about this
    await relief_email_handler.send_approval(email, name, relief.name)
    
    relief.is_active = True
    relief.phase = 'PREPARING'
    relief.updated_at = datetime.now()

    db.commit()
    
    return {"detail": "Relief effort successfully approved"}

@router.patch("/reject/{id}")
async def rejectReliefEffort(db:DB, id:int, res: Response, relief_email_handler: ReliefEmail, user: AuthDetails = Depends(get_current_user)):
    authorize(user, 4, 4)

    # TO FOLLOW: allow foundations to reject relief efforts so long
    # as organization is sponsored/supported by said foundation

    relief:ReliefEffort = db.query(ReliefEffort).filter(and_(ReliefEffort.id == id, ReliefEffort.is_deleted == False)).first()

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
async def deleteReliefEffort(db:DB, id:int, res: Response, relief_email_handler: ReliefEmail, user: AuthDetails = Depends(get_current_user)):
    authorize(user, 4, 4) # only admins can take down relief efforts

    relief:ReliefEffort = db.query(ReliefEffort).filter(and_(ReliefEffort.id == id, ReliefEffort.is_deleted == False)).first()

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
def retrieveBookmarks(db:DB, res:Response, user: AuthDetails = Depends(get_current_user)):
    authorize(user, 1, 4)
    print(user)
    bookmarks = db.query(ReliefBookmark).filter(and_(ReliefBookmark.user_id == user.user_id)).all()
    return bookmarks

@router.post("/{id}/bookmarks")
def bookmarkReliefEffort(db:DB, id:int, res:Response, user: AuthDetails = Depends(get_current_user)):
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

@router.delete("/{id}/bookmarks")
def unbookmarkReliefEffort(db:DB, id:int, res:Response, user: AuthDetails = Depends(get_current_user)):
    authorize(user, 1, 4)
    
    bookmark:ReliefBookmark = db.query(ReliefBookmark).filter(and_(ReliefBookmark.user_id == user.user_id, ReliefBookmark.relief_id == id)).first()

    if bookmark is None:
        res.status_code = 404
        return {"detail" : "Bookmark non-existent."}
    
    db.delete(bookmark)

    db.commit()

    return {"detail": "Relief effort unbookmarked"}

@router.get("/{id}/comments")
def getComments(db:DB, id:int, res:Response):
    comments = db.query(ReliefComment).filter(ReliefComment.id == id).all()
    return comments

class ReliefCommentDTO(BaseModel):
    message: str

@router.post("/{id}/comments")
def createComment(db:DB, id:int, body: ReliefCommentDTO, res:Response, user: AuthDetails = Depends(get_current_user)):
    # create and save comment
    authorize(user, 2, 4)

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
def deleteComment(db:DB, id:int, comment_id:int, res:Response, user: AuthDetails = Depends(get_current_user)):
    authorize(user, 2, 4)

    comment:ReliefComment = db.query(ReliefComment).filter(and_(ReliefComment.relief_id == id, ReliefComment.id == comment_id, ReliefComment.is_deleted == False)).first()

    if comment is None:
        res.status_code = 404
        return {"detail" : "Comment not found"}
    
    if user.level != 4 and user.user_id != comment.user_id:
        res.status_code = 403
        return {"detail" : "Forbidden deletion"}
    
    # mark comment as deleted
    comment.is_deleted = True

    db.commit()

    return {"detail": "Sucessfully deleted comment"}

@router.get("/{id}/updates")
def retrieveUpdates(db:DB, id:int, f: str = None):
    
    #updates:List[ReliefUpdate] = db.query(ReliefUpdate).filter(and_(ReliefUpdate.relief_id == id, ReliefUpdate.is_deleted == False))
    updates:List[ReliefUpdate] = List[ReliefUpdate]

    if f is not None:
        # also check if filter is valid here
        updates = db.query(ReliefUpdate).filter(and_(ReliefUpdate.relief_id == id, ReliefUpdate.is_deleted == False, ReliefUpdate.type == f)).all()
    else:
        # for none and/or invalid filters
        updates = db.query(ReliefUpdate).filter(and_(ReliefUpdate.relief_id == id, ReliefUpdate.is_deleted == False)).all()
        
    # apply filter later
    return updates

# endpoint to get images of updates
@router.get("/{id}/updates/{update_id}/images")
async def retrieveUpdateImages(db:DB, id:int, res:Response, update_id:int, file_handler:_fileHandler):
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
async def createUpdate(db:DB, id:int, file_handler:_fileHandler, res:Response, body: Json = Form(), images:List[UploadFile] = File(...), user: AuthDetails = Depends(get_current_user)):
    authorize(user, 2, 4)
    
    body:CreateUpdateDTO = json.loads(json.dumps(body), object_hook=lambda d: SimpleNamespace(**d))
    
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
    # validate images

    for image in images:
        if is_image_valid(image) == False:
            res.status_code = 400
            return {"detail" : "One of uploaded files are invalid."}
    
    update: ReliefUpdate = ReliefUpdate()

    update.title = body.title
    update.description = body.message
    update.relief_id = id
    update.type = body.type if hasattr(body, 'type') else 'General'

    db.add(update)
    db.commit()

    #    add images
    await file_handler.upload_multiple_file(images, id, f'relief-efforts/{id}/updates/{update.id}')

    return {"detail": "Successfully created update."}

class ReliefUpdateStatusDTO(BaseModel):
    owner_type: str
    owner_id: int
    phase: str

@router.patch("/{id}/phase")
async def updateReliefPhase(db:DB, id:int, res:Response, body: ReliefUpdateStatusDTO, user: AuthDetails = Depends(get_current_user)):
    authorize(user, 2, 5)
    
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