"""
Admin API Endpoints
===================
System health monitoring and metrics endpoints with FSM statistics.

Endpoints:
- GET /system/health: System health check with FSM statistics
- GET /metrics: Performance metrics
"""

from datetime import datetime
from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.models.responses import SystemHealth, SystemMetrics
from app.db.mongo import db_client
from app.db.fsm_repository import FSMTriageRepository
from app.engine.ml_model import predictor
from app.engine.circuit import circuit_breaker
from app.utils.dependencies import get_database
from app.config import settings


router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/system/health", response_model=SystemHealth)
async def get_system_health(
    database: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get system health status with FSM statistics.
    
    Perfect endpoint for Build2Break judge demonstrations showing:
    - FSM execution statistics
    - Honeypot trigger counts
    - HITL queue status
    - Circuit breaker state
    
    Returns:
        Health check status for all components + FSM metrics
    """
    # Check database connection
    db_connected = db_client.is_connected
    
    # Check ML model
    ml_loaded = predictor.is_loaded
    
    # Get circuit breaker state
    cb_status = circuit_breaker.get_status()
    
    # Get FSM statistics
    fsm_repo = FSMTriageRepository(database)
    fsm_stats = await fsm_repo.get_fsm_statistics()
    
    # Determine overall status
    if db_connected and ml_loaded:
        overall_status = "healthy"
    elif db_connected:
        overall_status = "degraded"
    else:
        overall_status = "unhealthy"
    
    return {
        "status": overall_status,
        "database_connected": db_connected,
        "ml_model_loaded": ml_loaded,
        "circuit_breaker_state": cb_status["state"],
        "timestamp": datetime.utcnow(),
        # FSM statistics for Build2Break judging
        "fsm_statistics": fsm_stats
    }


@router.get("/metrics", response_model=SystemMetrics)
async def get_metrics(
    database: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get system performance metrics.
    
    Returns:
        System metrics including circuit breaker status and database health
    """
    # Circuit breaker metrics
    cb_status = circuit_breaker.get_status()
    
    # Database metrics (basic)
    db_status = {
        "connected": db_client.is_connected,
        "database_name": settings.MONGO_DB_NAME
    }
    
    # Request metrics (placeholder)
    request_metrics = {
        "total_requests": 0,  # Would track with middleware
        "error_rate": 0.0,
        "avg_response_time_ms": 0
    }
    
    return SystemMetrics(
        circuit_breaker=cb_status,
        database_status=db_status,
        request_metrics=request_metrics,
        timestamp=datetime.utcnow()
    )
