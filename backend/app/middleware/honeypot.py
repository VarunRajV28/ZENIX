"""
Honeypot Middleware - Malicious Request Detection
================================================
Detects and blocks requests containing honeypot fields that should
never appear in legitimate API calls.

For Build2Break competition - catches automated attack tools.
"""

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Any
import json
from app.utils.logger import logger


class HoneypotMiddleware(BaseHTTPMiddleware):
    """
    Middleware to detect honeypot field injection attacks.
    
    Honeypot fields are deliberately undocumented fields that:
    - Should never appear in legitimate requests
    - Are commonly injected by automated scanners/fuzzers
    - Indicate malicious intent when present
    
    Examples: admin_debug_mode, __proto__, __debug__, is_admin
    """
    
    HONEYPOT_FIELDS = [
        # Admin elevation attempts
        "admin_debug_mode",
        "is_admin",
        "admin",
        "is_superuser",
        "debug_mode",
        
        # Prototype pollution (JavaScript attacks)
        "__proto__",
        "constructor",
        "prototype",
        
        # Debug/internal flags
        "__debug__",
        "_debug",
        "internal_mode",
        "test_mode",
        
        # SQL injection common fields
        "1=1",
        "' OR '1'='1",
        
        # NoSQL injection
        "$where",
        "$ne",
        "$gt",
        "$regex"
    ]
    
    def __init__(self, app, enabled: bool = True, log_to_db: bool = True):
        super().__init__(app)
        self.enabled = enabled
        self.log_to_db = log_to_db
    
    async def dispatch(self, request: Request, call_next):
        """
        Intercept request and check for honeypot fields.
        
        Args:
            request: Incoming FastAPI request
            call_next: Next middleware/endpoint in chain
        
        Returns:
            Response or 400 error if honeypot triggered
        """
        if not self.enabled:
            return await call_next(request)
        
        # Only check POST/PUT/PATCH requests with JSON body
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                # Read and cache request body
                body = await request.body()
                
                if body:
                    try:
                        payload = json.loads(body)
                        
                        # Check for honeypot fields
                        triggered_field = self._check_honeypot(payload)
                        
                        if triggered_field:
                            logger.warning(
                                f"Honeypot triggered! Field: {triggered_field} | "
                                f"Endpoint: {request.url.path} | "
                                f"IP: {request.client.host if request.client else 'unknown'}"
                            )
                            
                            # Log to database if enabled
                            if self.log_to_db:
                                await self._log_honeypot_trigger(
                                    request=request,
                                    triggered_field=triggered_field,
                                    payload=payload
                                )
                            
                            # Return 400 Bad Request (don't reveal it's a honeypot)
                            raise HTTPException(
                                status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Invalid request structure"
                            )
                    
                    except json.JSONDecodeError:
                        pass  # Not JSON, let validation handle it
            
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Honeypot middleware error: {str(e)}")
        
        return await call_next(request)
    
    def _check_honeypot(self, payload: Any, path: str = "") -> str:
        """
        Recursively check payload for honeypot fields.
        
        Args:
            payload: Request payload (dict, list, or primitive)
            path: Current JSON path (for nested objects)
        
        Returns:
            Triggered field name or empty string
        """
        if isinstance(payload, dict):
            for key, value in payload.items():
                # Check if key itself is a honeypot
                if key.lower() in [f.lower() for f in self.HONEYPOT_FIELDS]:
                    return f"{path}.{key}" if path else key
                
                # Check for suspicious patterns in key names
                if any(pattern in key.lower() for pattern in ["admin", "debug", "__", "$"]):
                    if key.lower() in [f.lower() for f in self.HONEYPOT_FIELDS]:
                        return f"{path}.{key}" if path else key
                
                # Recursively check nested objects
                nested_path = f"{path}.{key}" if path else key
                triggered = self._check_honeypot(value, nested_path)
                if triggered:
                    return triggered
        
        elif isinstance(payload, list):
            for i, item in enumerate(payload):
                triggered = self._check_honeypot(item, f"{path}[{i}]")
                if triggered:
                    return triggered
        
        return ""
    
    async def _log_honeypot_trigger(
        self,
        request: Request,
        triggered_field: str,
        payload: dict
    ) -> None:
        """
        Log honeypot trigger to database for security monitoring.
        
        Args:
            request: FastAPI request object
            triggered_field: Field that triggered honeypot
            payload: Request payload (sanitized)
        """
        try:
            # Get database from app state
            from app.db.fsm_repository import FSMTriageRepository
            
            if hasattr(request.app.state, "database"):
                fsm_repo = FSMTriageRepository(request.app.state.database)
                
                # Sanitize payload (remove sensitive data)
                sanitized_payload = {
                    k: "***REDACTED***" if k in ["password", "token", "secret"] else v
                    for k, v in payload.items()
                }
                
                await fsm_repo.log_honeypot_alert(
                    triggered_field=triggered_field,
                    endpoint=request.url.path,
                    ip_address=request.client.host if request.client else None,
                    user_agent=request.headers.get("user-agent"),
                    request_payload=sanitized_payload
                )
        
        except Exception as e:
            logger.error(f"Failed to log honeypot alert: {str(e)}")


def create_honeypot_middleware(enabled: bool = True, log_to_db: bool = True):
    """
    Factory function to create honeypot middleware with configuration.
    
    Args:
        enabled: Enable/disable honeypot detection
        log_to_db: Log triggers to database
    
    Returns:
        Configured middleware instance
    """
    def middleware(app):
        return HoneypotMiddleware(app, enabled=enabled, log_to_db=log_to_db)
    
    return middleware
