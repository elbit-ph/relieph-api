from models.auth_details import AuthDetails
from fastapi import APIRouter, Depends, HTTPException, status
from services.db.models import User, Organization
from sqlalchemy.orm import and_

def authorize(user: AuthDetails, min_level: int = 0, max_level: int = 5):
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Sign in first"
        )
    #if user.level < min_level:
    if user.level not in range(min_level, max_level+1):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No access for user type."
        )

def is_user_organizer(user: AuthDetails, org_id:int, db):
    # get organization
    org:Organization = db.query(Organization).filter(and_(Organization.id == org_id, Organization.is_active == True)).first()
    
    # check if org exists
    if org is None:
        return False
    
    # check if user can act on behalf of org
    if org.owner_id != user.user_id:
        return False

    return True

def is_authorized(owner_id:int, owner_type:str, user: AuthDetails, db):
    # admins are automatically authorized
    if user.level == 4:
        return True
    # check authorization based on owner type
    match owner_type:
        case 'USER':
            if user.user_id != owner_id:
                return False
        case 'ORGANIZATION':
            if is_user_organizer(user, owner_id, db) == False:
                return False
        case _:
            return False
    return True