from typing import Annotated
from fastapi import APIRouter, Depends, UploadFile, HTTPException, status, Response, Body
from dependencies import get_db_session, get_logger, get_s3_handler, get_current_user, get_relief_email_handler
from services.db.database import Session
from services.db.models import Organization, User, Address, ReliefEffort, ReliefBookmark, ReliefComment
from services.log.log_handler import LoggingService
from services.aws.s3_handler import S3_Handler
from services.email.relief_email_handler import ReliefEmailHandler
from models.auth_details import AuthDetails
from util.auth.auth_tool import authorize
from pydantic import BaseModel
from datetime import datetime, date
from sqlalchemy import and_

router = APIRouter(
    prefix="/reliefs",
    tags=["reliefs"],
    dependencies=[Depends(get_db_session), Depends(get_logger)]
)

DB = Annotated[Session, Depends(get_db_session)]
Logger = Annotated[LoggingService, Depends(get_logger)]
S3Handler = Annotated[S3_Handler, Depends(get_s3_handler)]
ReliefEmail = Annotated[ReliefEmailHandler, Depends(get_relief_email_handler)]

@router.get("/")
def retrieveReliefEfforts(db: DB, p: int = 1, c: int = 10):
    return db.query(ReliefEffort).limit(c).offset((p-1)*c).all()

@router.get("/{id}")
def retrieveReliefEffort(db:DB, id:int):
    relief:ReliefEffort = db.query(ReliefEffort).filter(ReliefEffort.id == id).first()

    if relief is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found."
        )
    
    return relief

class CreateReliefEffortDTO(BaseModel):
    # owner_id: int
    # owner_type: str
    disaster_type: str  
    name: str
    description: str
    purpose: str
    monetary_goal: float
    start_date: date
    end_date: date

@router.post("/user")
def createReliefEffortAsIndividual(db:DB, res: Response, body: CreateReliefEffortDTO, user: AuthDetails = Depends(get_current_user)):
    authorize(user, 2, 5)
    
    # IDEA: check how many relief effort an individual first has
    # limit the amount of relief effort an indivdual can create

    # validate input
    if body.start_date < date.today() or body.end_date < date.today():
        res.status_code = 400
        return {
            "detail" : "Invalid date input."
        }

    relief:ReliefEffort = ReliefEffort()
    relief.owner_id = user.user_id
    relief.owner_type = 'USER'
    relief.name = body.name
    relief.description = body.description
    relief.purpose = body.purpose
    relief.disaster_type = body.disaster_type
    relief.monetary_goal = body.monetary_goal
    relief.start_date = body.start_date
    relief.end_date = body.end_date
    relief.phase = 'For Approval'

    db.add(relief)
    db.commit()

    return {"detail": "Relief effort successfully created"}

@router.post("/organization/{id}")
def createReliefEffortAsOrganization(db:DB, id:int, res: Response, body: CreateReliefEffortDTO, user: AuthDetails = Depends(get_current_user)):
    authorize(user, 2, 5)

    # IDEA: check how many relief effort an individual first has
    # limit the amount of relief effort an indivdual can create

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

    relief:ReliefEffort = ReliefEffort()
    relief.owner_id = id
    relief.owner_type = 'ORGANIZATION'
    relief.name = body.name
    relief.description = body.description
    relief.purpose = body.purpose
    relief.disaster_type = body.disaster_type
    relief.monetary_goal = body.monetary_goal
    relief.start_date = body.start_date
    relief.end_date = body.end_date

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
    authorize(user, 5, 5)

    # TO FOLLOW: allow foundations to approve relief efforts so long
    # as organization is sponsored/supported by said foundation

    relief:ReliefEffort = db.query(ReliefEffort).filter(and_(ReliefEffort.id == id, ReliefEffort.is_active == False, ReliefEffort.is_deleted == False)).first()

    if relief is None:
        res.status_code = 404
        return {"detail": "Relief effort non-existent."}
    
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
    await relief_email_handler.send_approval(email, name, relief.name)
    
    relief.is_active = True
    relief.updated_at = datetime.now()

    db.commit()
    
    return {"detail": "Relief effort successfully approved"}

@router.patch("/reject/{id}")
async def rejectReliefEffort(db:DB, id:int, res: Response, relief_email_handler: ReliefEmail, user: AuthDetails = Depends(get_current_user)):
    authorize(user, 5, 5)

    # TO FOLLOW: allow foundations to reject relief efforts so long
    # as organization is sponsored/supported by said foundation

    relief:ReliefEffort = db.query(ReliefEffort).filter(and_(ReliefEffort.id == id, ReliefEffort.is_deleted == False)).first()

    if relief is None:
        res.status_code = 404
        return {"detail": "Relief effort non-existent."}
    
    relief.is_deleted = True
    relief.is_active = False
    relief.phase = 'Rejected'
    relief.updated_at = datetime.now()

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
    await relief_email_handler.send_rejection(email, name, relief.name)

    db.commit()

    return {"detail": "Relief effort successfully rejected."}

@router.delete("/{id}")
async def deleteReliefEffort(db:DB, id:int, res: Response, relief_email_handler: ReliefEmail, user: AuthDetails = Depends(get_current_user)):
    authorize(user, 5, 5) # only admins can take down relief efforts

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
    authorize(user, 1,5)
    print(user)
    bookmarks = db.query(ReliefBookmark).filter(and_(ReliefBookmark.user_id == user.user_id)).all()
    return bookmarks

@router.post("/{id}/bookmarks")
def bookmarkReliefEffort(db:DB, id:int, res:Response, user: AuthDetails = Depends(get_current_user)):
    authorize(user, 1, 5)

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
    authorize(user, 1, 5)
    
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
    authorize(user, 2, 5)

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
    authorize(user, 2,5)

    comment:ReliefComment = db.query(ReliefComment).filter(and_(ReliefComment.relief_id == id, ReliefComment.id == comment_id, ReliefComment.is_deleted == False)).first()

    if comment is None:
        res.status_code = 404
        return {"detail" : "Comment not found"}
    
    if user.level != 5 and user.user_id != comment.user_id:
        res.status_code = 403
        return {"detail" : "Forbidden deletion"}
    
    # mark comment as deleted
    comment.is_deleted = True

    db.commit()

    return {"detail": "Sucessfully deleted comment"}