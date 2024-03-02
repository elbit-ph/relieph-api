from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile

from dependencies import get_db_session, get_logger, get_s3_handler
from services.db.database import Session
from services.db.models import User
from services.log.log_handler import LoggingService
from services.aws.s3_handler import S3_Handler

router = APIRouter(
    prefix="/test",
    tags=["test"],
    dependencies=[Depends(get_db_session), Depends(get_logger)]
)

DB = Annotated[Session, Depends(get_db_session)]
Logger = Annotated[LoggingService, Depends(get_logger)]
S3Handler = Annotated[S3_Handler, Depends(get_s3_handler)]

@router.get("/")
async def get_test(logger: Logger, s3handler: S3Handler):
    #logger.log_warning(__file__, 'get_test', 'test')
    s3handler.download_image(1, 'users')
    return {"message":"Hello World!"}

@router.get("/db-tests")
async def get_db(db: DB):
    return {"user count": db.query(User).all()}

@router.post("/upload-img/{id}")
async def post_img(file: UploadFile, id:int, s3handler: S3Handler):
    # `file` is under multipart
    await s3handler.upload_single_image(file, id, 'users')
    return {"filename": file.filename}

@router.get("/get-user-profile/{id}")
async def get_user_img(id:int, s3handler: S3Handler):
    resu = s3handler.get_image(id, 'users')
    if resu[1] != True:
        return {'Error':'Invalid'}
    return {'link':resu[0]}