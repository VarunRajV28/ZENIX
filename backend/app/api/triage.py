"""
Triage API Endpoint - Main Health Assessment
=============================================
POST /triage: Idempotent, circuit-broken maternal health assessment

Features:
- Idempotency key support (x-idempotency-key header)
- Circuit breaker protection for ML model
- Comprehensive risk assessment through 3-layer pipeline
- Audit trail logging
"""

import hashlib
import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Header, Response
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.models.requests import TriageRequest
from app.models.responses import TriageResponse
from app.db.repositories import TriageRepository, IdempotencyRepository
from app.db.schemas import TriageLogDocument, IdempotencyKeyDocument, RiskLevel
from app.engine.orchestrator import assess_maternal_risk
from app.utils.dependencies import get_database, get_current_user, get_idempotency_key
from app.utils.logger import logger


router = APIRouter(tags=["Triage"])


@router.post("/triage", response_model=TriageResponse)
async def submit_triage(
    request: TriageRequest,
    response: Response,
    idempotency_key: Optional[str] = Depends(get_idempotency_key),
    current_user: dict = Depends(get_current_user),
    database: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Submit maternal health triage assessment.
    
    This endpoint is idempotent - duplicate requests with the same idempotency
    key within 10 minutes will return the cached response.
    
    Args:
        request: Triage request with clinical vitals
        idempotency_key: Optional UUID for request deduplication
        current_user: Authenticated user
        database: Database connection
    
    Returns:
        Comprehensive risk assessment
    
    Headers:
        x-idempotency-key: UUID for request deduplication (optional)
        X-Idempotent-Replay: true (if cached response returned)
    """
    user_id = current_user["_id"]
    
    logger.info(
        f"Triage request received for user: {user_id}",
        extra={"idempotency_key": idempotency_key}
    )
    
    # =========================================================================
    # IDEMPOTENCY CHECK
    # =========================================================================
    idempotency_repo = IdempotencyRepository(database)
    
    if idempotency_key:
        # Check for cached response
        cached_response = await idempotency_repo.get_cached_response(idempotency_key)
        
        if cached_response:
            logger.info(
                f"Idempotency cache HIT: {idempotency_key}",
                extra={"user_id": user_id}
            )
            # Set header to indicate this is a replayed response
            response.headers["X-Idempotent-Replay"] = "true"
            return TriageResponse(**cached_response)
    
    # =========================================================================
    # RISK ASSESSMENT PIPELINE
    # =========================================================================
    try:
        # Run comprehensive assessment
        assessment = await assess_maternal_risk(request.vitals)
        
        # Store in triage logs
        triage_repo = TriageRepository(database)
        triage_log = TriageLogDocument(
            user_id=user_id,
            age=request.vitals.age,
            systolic_bp=request.vitals.systolic_bp,
            diastolic_bp=request.vitals.diastolic_bp,
            blood_sugar=request.vitals.blood_sugar,
            body_temp=request.vitals.body_temp,
            heart_rate=request.vitals.heart_rate,
            blood_oxygen=request.vitals.blood_oxygen,
            gestational_weeks=request.vitals.gestational_weeks,
            risk_level=RiskLevel(assessment["risk_level"]),
            confidence=assessment["confidence"],
            alerts=assessment["alerts"],
            clinical_notes=assessment["clinical_notes"],
            feature_importances=assessment.get("feature_importances"),
            engine_source=assessment["engine_source"],
            fallback_active=assessment["fallback_active"],
            zudu_insights=assessment.get("zudu_insights"),
            processing_time_ms=assessment["processing_time_ms"],
            timestamp=assessment["timestamp"]
        )
        
        log_id = await triage_repo.create_triage_log(triage_log)
        
        # Build response
        triage_response = TriageResponse(
            assessment_id=log_id,
            risk_level=assessment["risk_level"].value if hasattr(assessment["risk_level"], "value") else assessment["risk_level"],
            confidence=assessment["confidence"],
            alerts=assessment["alerts"],
            clinical_notes=assessment["clinical_notes"],
            feature_importances=assessment.get("feature_importances", {}),
            engine_source=assessment["engine_source"],
            fallback_active=assessment["fallback_active"],
            zudu_insights=assessment.get("zudu_insights"),
            timestamp=assessment["timestamp"],
            processing_time_ms=assessment["processing_time_ms"]
        )
        
        # =====================================================================
        # STORE IDEMPOTENCY KEY
        # =====================================================================
        if idempotency_key:
            # Create request hash for verification
            request_hash = hashlib.sha256(
                json.dumps(request.vitals.model_dump(), sort_keys=True).encode()
            ).hexdigest()
            
            idempotency_doc = IdempotencyKeyDocument(
                idempotency_key=idempotency_key,
                user_id=user_id,
                request_hash=request_hash,
                response_data=triage_response.model_dump()
            )
            
            await idempotency_repo.store_response(idempotency_doc)
        
        logger.info(
            f"Triage assessment completed: {triage_response.risk_level}",
            extra={
                "user_id": user_id,
                "log_id": log_id,
                "engine": assessment["engine_source"]
            }
        )
        
        return triage_response
    
    except ValueError as e:
        # Pydantic validation error or adversarial input
        logger.warning(f"Validation error in triage: {str(e)}", extra={"user_id": user_id})
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error_type": "VALIDATION_ERROR",
                "message": str(e)
            }
        )
    
    except Exception as e:
        logger.error(
            f"Triage assessment failed: {str(e)}",
            extra={"user_id": user_id},
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during assessment"
        )
