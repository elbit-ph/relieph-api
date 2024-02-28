from typing import Annotated
from fastapi import Header, HTTPException

from services.db.database import Session
from services.storage.cache_handler import CacheHandler
from services.email.email_handler import EmailHandler

# dependencies go here

async def get_db_session():
    return Session()

async def get_cache_handler():
    return CacheHandler()

async def get_email_handler():
    return EmailHandler()

# add JWT support here