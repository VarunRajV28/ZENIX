"""
Security Utilities - Password Hashing & JWT Token Management
=============================================================
Implements bcrypt password hashing and JWT token encoding/decoding.

Security Considerations:
- Passwords are never stored in plaintext
- JWT tokens are signed with HS256
- Token expiration is enforced
- All operations are logged for audit trails
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.config import settings
from app.utils.logger import logger, log_security_event


# Bcrypt context for password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """
    Hash password using bcrypt.
    
    Args:
        password: Plain text password
    
    Returns:
        Hashed password string
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify password against hashed version.
    
    Args:
        plain_password: User-provided password
        hashed_password: Stored password hash
    
    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT access token.
    
    Args:
        data: Payload data to encode (must include 'sub' for user_id)
        expires_delta: Token expiration time (default: from settings)
    
    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRATION_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow()
    })
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM
    )
    
    logger.debug(f"Created JWT token for user: {data.get('sub')}")
    return encoded_jwt


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode and validate JWT access token.
    
    Args:
        token: JWT token string
    
    Returns:
        Decoded token payload if valid, None otherwise
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM]
        )
        user_id: str = payload.get("sub")
        
        if user_id is None:
            log_security_event("token_invalid", "unknown", {"reason": "missing_sub"})
            return None
        
        return payload
    
    except JWTError as e:
        log_security_event("token_invalid", "unknown", {"error": str(e)})
        return None


def create_refresh_token(user_id: str) -> str:
    """
    Create a long-lived refresh token.
    
    Args:
        user_id: User identifier
    
    Returns:
        Encoded refresh token
    """
    return create_access_token(
        data={"sub": user_id, "type": "refresh"},
        expires_delta=timedelta(days=30)
    )
