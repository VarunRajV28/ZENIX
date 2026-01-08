"""
Authentication API Endpoints
=============================
Handles user registration, login, and token refresh.

Endpoints:
- POST /auth/register: Create new user account
- POST /auth/login: Authenticate and receive JWT token
- POST /auth/refresh: Refresh expired token
"""

from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.models.requests import RegisterRequest, LoginRequest
from app.models.responses import TokenResponse
from app.db.repositories import UserRepository
from app.db.schemas import UserDocument, UserRole
from app.utils.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token
)
from app.utils.dependencies import get_database
from app.utils.logger import logger, log_security_event
from app.config import settings


router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    database: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Register new user account.
    
    Args:
        request: Registration data
        database: Database connection
    
    Returns:
        JWT token and user information
    
    Raises:
        HTTPException: If email already exists
    """
    user_repo = UserRepository(database)
    
    # Check if email already exists
    existing_user = await user_repo.get_user_by_email(request.email)
    if existing_user:
        log_security_event("registration_failed", request.email, {"reason": "email_exists"})
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )
    
    # Create user document
    user_data = UserDocument(
        email=request.email,
        hashed_password=hash_password(request.password),
        full_name=request.full_name,
        role=UserRole(request.role),
        age=request.age,
        phone=request.phone,
        gestational_weeks=request.gestational_weeks,
        pre_existing_conditions=request.pre_existing_conditions,
        specialization=request.specialization,
        license_number=request.license_number
    )
    
    # Save to database
    user_id = await user_repo.create_user(user_data)
    
    logger.info(f"New user registered: {request.email} (role: {request.role})")
    
    # Generate JWT token
    access_token = create_access_token(
        data={"sub": user_id, "role": request.role}
    )
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.JWT_EXPIRATION_MINUTES * 60,
        user_id=user_id,
        role=request.role,
        full_name=request.full_name
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    database: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Authenticate user and return JWT token.
    
    Args:
        form_data: OAuth2 form with username (email) and password
        database: Database connection
    
    Returns:
        JWT token and user information
    
    Raises:
        HTTPException: If credentials invalid
    """
    user_repo = UserRepository(database)
    
    # Find user by email
    user = await user_repo.get_user_by_email(form_data.username)
    
    if not user:
        log_security_event("login_failed", form_data.username, {"reason": "user_not_found"})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify password
    if not verify_password(form_data.password, user["hashed_password"]):
        log_security_event("login_failed", user["_id"], {"reason": "invalid_password"})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if account is active
    if not user.get("is_active", True):
        log_security_event("login_failed", user["_id"], {"reason": "account_inactive"})
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive"
        )
    
    logger.info(f"User logged in: {user['email']} (role: {user['role']})")
    
    # Generate JWT token
    access_token = create_access_token(
        data={"sub": user["_id"], "role": user["role"]}
    )
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.JWT_EXPIRATION_MINUTES * 60,
        user_id=user["_id"],
        role=user["role"],
        full_name=user["full_name"]
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    current_user: dict = Depends(get_database)
):
    """
    Refresh JWT token (placeholder for future implementation).
    
    Returns:
        New JWT token
    """
    # This would verify the refresh token and issue a new access token
    # For now, we'll keep it simple and just return a new token
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Token refresh not yet implemented"
    )
