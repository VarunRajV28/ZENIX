"""
FastAPI Dependency Injection - Shared Dependencies
===================================================
Provides reusable dependencies for authentication and database access.
"""

from typing import Optional
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordBearer
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.db.mongo import db_client
from app.utils.security import decode_access_token
from app.utils.logger import log_security_event


# OAuth2 scheme for token extraction
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_database() -> AsyncIOMotorDatabase:
    """
    Dependency to get database instance.
    
    Returns:
        AsyncIOMotorDatabase instance
    """
    return db_client.get_database()


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    database: AsyncIOMotorDatabase = Depends(get_database)
) -> dict:
    """
    Dependency to get current authenticated user.
    
    Args:
        token: JWT token from Authorization header
        database: Database instance
    
    Returns:
        User document
    
    Raises:
        HTTPException: If token invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Decode token
    payload = decode_access_token(token)
    if payload is None:
        log_security_event("invalid_token", "unknown", {"reason": "decode_failed"})
        raise credentials_exception
    
    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_exception
    
    # Fetch user from database
    from app.db.repositories import UserRepository
    user_repo = UserRepository(database)
    user = await user_repo.get_user_by_id(user_id)
    
    if user is None:
        log_security_event("user_not_found", user_id, {})
        raise credentials_exception
    
    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    return user


async def get_current_doctor(
    current_user: dict = Depends(get_current_user)
) -> dict:
    """
    Dependency to ensure current user is a doctor.
    
    Args:
        current_user: Current authenticated user
    
    Returns:
        User document if doctor
    
    Raises:
        HTTPException: If user is not a doctor
    """
    if current_user.get("role") != "doctor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint requires doctor privileges"
        )
    return current_user


async def get_current_mother(
    current_user: dict = Depends(get_current_user)
) -> dict:
    """
    Dependency to ensure current user is a mother.
    
    Args:
        current_user: Current authenticated user
    
    Returns:
        User document if mother
    
    Raises:
        HTTPException: If user is not a mother
    """
    if current_user.get("role") != "mother":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint requires mother privileges"
        )
    return current_user


async def get_idempotency_key(
    x_idempotency_key: Optional[str] = Header(None)
) -> Optional[str]:
    """
    Extract idempotency key from request headers.
    
    Args:
        x_idempotency_key: Idempotency key from header
    
    Returns:
        Idempotency key or None
    """
    return x_idempotency_key
