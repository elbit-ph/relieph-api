from models.auth_details import AuthDetails
from fastapi import APIRouter, Depends, HTTPException, status

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