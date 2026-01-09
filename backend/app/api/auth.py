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
    
    # SL-1 Security Fix: Validate invite code for doctor role registration
    if request.role == "doctor":
        if not request.invite_code:
            log_security_event("registration_failed", request.email, {"reason": "missing_invite_code", "role": "doctor"})
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Doctor registration requires a valid invite code"
            )
        
        # Verify invite code exists and is valid
        invite_collection = database.invite_codes
        invite_doc = await invite_collection.find_one({"code": request.invite_code})
        
        if not invite_doc:
            log_security_event("registration_failed", request.email, {"reason": "invalid_invite_code"})
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid invite code"
            )
        
        if invite_doc.get("is_used", False):
            log_security_event("registration_failed", request.email, {"reason": "invite_code_reused"})
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invite code has already been used"
            )
        
        # Check if invite code has expired
        if "expires_at" in invite_doc:
            from datetime import datetime, timezone
            expires_at = invite_doc["expires_at"]
            # Ensure timezone-aware comparison
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) > expires_at:
                log_security_event("registration_failed", request.email, {"reason": "invite_code_expired"})
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Invite code has expired"
                )
        
        logger.info(f"Invite code validated for doctor registration: {request.invite_code}")
    
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
    
    # Mark invite code as used (for doctor role)
    if request.role == "doctor" and request.invite_code:
        invite_collection = database.invite_codes
        await invite_collection.update_one(
            {"code": request.invite_code},
            {"$set": {"is_used": True, "used_by": user_id, "used_at": user_data.created_at}}
        )
        logger.info(f"Invite code {request.invite_code} marked as used")
    
    logger.info(f"New user registered: {request.email} (role: {request.role})")
    log_security_event("registration_success", request.email, {"role": request.role, "user_id": user_id})
    
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
