"""
FastAPI Main Application
=========================
Entry point for MomWatch AI backend with:
- CORS configuration
- Global exception handlers
- Lifespan events (startup/shutdown)
- API router registration
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from pymongo.errors import PyMongoError
from app.config import settings
from app.db.mongo import db_client
from app.engine.ml_model import predictor, MLModelException
from app.engine.circuit import CircuitBreakerOpen
from app.engine.zudu_integration import zudu_client, ZuduAPIException
from app.utils.logger import logger
from app.api import auth, triage, doctor, mother, admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    """
    # =========================================================================
    # STARTUP
    # =========================================================================
    logger.info("=" * 70)
    logger.info("MomWatch AI Backend - Starting up...")
    logger.info("=" * 70)
    
    # Connect to MongoDB
    try:
        await db_client.connect()
        logger.info("✓ Database connected")
    except Exception as e:
        logger.critical(f"✗ Database connection failed: {str(e)}")
        raise
    
    # Load ML model
    try:
        predictor.load_model()
        logger.info("✓ ML model loaded")
    except MLModelException as e:
        logger.warning(f"⚠ ML model not loaded: {str(e)}")
        logger.warning("System will operate in fallback mode (clinical rules only)")
    
    # Initialize Zudu AI client
    if settings.ZUDU_API_KEY and settings.ZUDU_API_KEY != "your_zudu_api_key_here":
        logger.info("✓ Zudu AI configured")
    else:
        logger.warning("⚠ Zudu AI not configured (optional)")
    
    logger.info("=" * 70)
    logger.info("MomWatch AI Backend - Ready to serve requests")
    logger.info(f"API Host: {settings.API_HOST}:{settings.API_PORT}")
    logger.info(f"CORS Origins: {settings.CORS_ORIGINS}")
    logger.info("=" * 70)
    
    yield
    
    # =========================================================================
    # SHUTDOWN
    # =========================================================================
    logger.info("MomWatch AI Backend - Shutting down...")
    
    # Close database connection
    await db_client.close()
    logger.info("✓ Database connection closed")
    
    # Close Zudu AI session
    await zudu_client.close()
    logger.info("✓ Zudu AI client closed")
    
    logger.info("MomWatch AI Backend - Shutdown complete")


# =============================================================================
# FastAPI Application
# =============================================================================
app = FastAPI(
    title="MomWatch AI",
    description="Production-grade maternal health monitoring system with ML risk assessment",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# =============================================================================
# CORS Middleware
# =============================================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# Global Exception Handlers
# =============================================================================

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handle Pydantic validation errors with detailed field-level feedback.
    """
    logger.warning(
        f"Validation error: {exc.errors()}",
        extra={"path": request.url.path}
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error_type": "VALIDATION_ERROR",
            "detail": exc.errors(),
            "body": exc.body
        }
    )


@app.exception_handler(ValidationError)
async def pydantic_validation_handler(request: Request, exc: ValidationError):
    """
    Handle Pydantic validation errors.
    """
    logger.warning(
        f"Pydantic validation error: {exc.errors()}",
        extra={"path": request.url.path}
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error_type": "VALIDATION_ERROR",
            "detail": exc.errors()
        }
    )


@app.exception_handler(PyMongoError)
async def mongodb_exception_handler(request: Request, exc: PyMongoError):
    """
    Handle MongoDB errors with 503 Service Unavailable.
    """
    logger.error(
        f"MongoDB error: {str(exc)}",
        extra={"path": request.url.path},
        exc_info=True
    )
    
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "error_type": "DATABASE_ERROR",
            "detail": "Database temporarily unavailable. Please try again later."
        }
    )


@app.exception_handler(CircuitBreakerOpen)
async def circuit_breaker_handler(request: Request, exc: CircuitBreakerOpen):
    """
    Handle circuit breaker open state (not an error, just fallback mode).
    """
    logger.info(
        f"Circuit breaker open: {str(exc)}",
        extra={"path": request.url.path}
    )
    
    # Return 200 OK with fallback_active flag
    # This is not an error - system is working in degraded mode
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "ML model temporarily unavailable. Using clinical rules fallback.",
            "fallback_active": True
        }
    )


@app.exception_handler(MLModelException)
async def ml_model_exception_handler(request: Request, exc: MLModelException):
    """
    Handle ML model errors.
    """
    logger.error(
        f"ML model error: {str(exc)}",
        extra={"path": request.url.path},
        exc_info=True
    )
    
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "error_type": "ML_MODEL_ERROR",
            "detail": "ML model temporarily unavailable. Using fallback assessment."
        }
    )


@app.exception_handler(ZuduAPIException)
async def zudu_exception_handler(request: Request, exc: ZuduAPIException):
    """
    Handle Zudu AI API errors (non-critical).
    """
    logger.warning(
        f"Zudu AI error: {str(exc)}",
        extra={"path": request.url.path}
    )
    
    # Zudu AI is optional, so we don't fail the request
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "Zudu AI unavailable, continuing with standard assessment.",
            "zudu_available": False
        }
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """
    Catch-all handler for unexpected errors.
    """
    logger.error(
        f"Unexpected error: {str(exc)}",
        extra={"path": request.url.path},
        exc_info=True
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error_type": "INTERNAL_SERVER_ERROR",
            "detail": "An unexpected error occurred. Please contact support if this persists."
        }
    )


# =============================================================================
# API Routers
# =============================================================================
app.include_router(auth.router)
app.include_router(triage.router)
app.include_router(doctor.router)
app.include_router(mother.router)
app.include_router(admin.router)


# =============================================================================
# Root Endpoint
# =============================================================================
@app.get("/")
async def root():
    """
    Root endpoint with API information.
    """
    return {
        "name": "MomWatch AI",
        "version": "1.0.0",
        "description": "Maternal health monitoring system with ML risk assessment",
        "status": "operational",
        "docs": "/docs",
        "health": "/admin/system/health"
    }


@app.get("/health")
async def health_check():
    """
    Simple health check endpoint.
    """
    return {
        "status": "ok",
        "timestamp": "2026-01-08T00:00:00"
    }
