from typing import Annotated
from fastapi import Header, HTTPException

from services.db.database import Session
from services.storage.cache_handler import CacheHandler
from services.email.email_handler import EmailHandler
from services.log.log_handler import LoggingService
from services.aws.s3_handler import S3_Handler

# dependencies go here

async def get_db_session():
    return Session()

async def get_cache_handler():
    return CacheHandler()

async def get_email_handler():
    return EmailHandler()

def get_logger():
    return LoggingService('file.log')

def get_s3_handler():
    return S3_Handler()

# add JWT support here