from typing import Annotated, List
from fastapi import APIRouter, Depends, UploadFile, HTTPException, status, Response, Body, Form
from dependencies import get_logger, get_current_user, get_code_email_handler, get_file_handler
from services.db.database import Session
from services.db.models import User, Address, UserUpgradeRequest, VerificationCode, SponsorshipRequest, Organization, Report
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
from services.reports.reports_handler import ReportsHandler

router = APIRouter(
    prefix="/reports",
    tags=["reports"],
    dependencies=[]
)

valid_types = ['comments', 'relief', 'organization']
valid_statuses = ['pending', 'resolved', 'deleted', 'all']

db = Session()
report_handler = ReportsHandler()

@router.get("/comments")
def retrieve_reports(type:str, res:Response, p:int = 1, c:int = 10, status:str='pending', user:AuthDetails = Depends(get_current_user)):
    """
    Retrieves reports on comment. Takes `c` entries of page `p` with status `status`
    """

    # check authorization
    authorize(user, 4, 4)

    resu = report_handler.retrieve_reports(type, status)

    if resu[1] == True:
        return resu[0]

    match resu[0]:
        case 'InvalidStatus':
            res.status_code = 400
            return {'detail': 'Invalid status entered.'}
        case 'InvalidType':
            res.status_code = 400
            return {'detail': 'Invalid type entered.'}
        case _:
            res.status_code = 500
            return {'detail': 'Server error.'}

@router.get("/{report_id}")
def retrieve_report(report_id:int, type:str, res:Response, user:AuthDetails = Depends(get_current_user)):
    """
    Retrieves report identified by `report_id`
    """
    
    # checks for authorization
    authorize(user, 4, 4)

    if type not in valid_types:
        res.status_code = 400
        return {'detail' : 'Invalid type.'}
    
    report = db.query(Report).filter(and_(Report.is_deleted == False, Report.id == report_id)).first()

    # check if report exists
    if report == None:
        res.status_code = 404
        return {'detail' : 'Report non-existent'}

    return report

class CreateReportDTO(BaseModel):
    target_id:int
    target_type:str
    reason:str

@router.post('/')
def create_report(body:CreateReportDTO, res:Response, user:AuthDetails = Depends(get_current_user)):
    """
    Creates report.
    """

    # check for authorization
    authorize(user, 1, 4)
    
    resu = report_handler.create_report(body.target_type, body.target_id, body.reason, user.user_id)

    # check if report creation was a success
    if resu[1] == True:
        return {'detail': 'Target exists.'}

    match resu[0]:
        case 'InvalidType':
            res.status_code = 400
            return {'detail': 'Target type invalid.'}
        case 'InvalidType':
            res.status_code = 400
            return {'detail': 'Target not found.'}
        case _:
            res.status_code = 500
            return {'detail': 'Internal server error.'}
        
@router.patch('/takedown/{report_id}')
def takedown(report_id:int, res:Response, user:AuthDetails = Depends(get_current_user)):
    """
    Takes down a piece of content. Requires admin access.
    """
    
    authorize(user, 4, 4)

    resu = report_handler.takedown_target(report_id)

    if resu[1] == True:
        return {'detail': 'Item taken down.'}
    
    match resu[0]:
        case _:
            res.status_code = 500
            return {'detail': 'Internal server error.'}

@router.patch('/resolve/{report_id}')
def resolve(report_id:int, res:Response, user:AuthDetails = Depends(get_current_user)):
    """
    Marks report as resolved and not alarming. Requires admin access.
    """
    
    authorize(user, 4, 4)

    resu = report_handler.resolve_target(report_id)

    if resu[1] == True:
        return {'detail': 'Item taken down.'}
    
    match resu[0]:
        case _:
            res.status_code = 500
            return {'detail': 'Internal server error.'}