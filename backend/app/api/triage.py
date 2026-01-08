"""
Triage API Endpoint - FSM-based Health Assessment
=================================================
POST /triage: Idempotent, FSM-orchestrated maternal health assessment

Features:
- Finite State Machine architecture for deterministic flow
- Honeypot detection (handled by middleware)
- Idempotency with client_sync_uuid
- Human-in-the-Loop integration for low confidence cases
- Complete FSM trace for debugging
- Circuit breaker protection for ML model
"""

import hashlib
import json
import uuid
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Header, Response
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.models.requests import TriageRequest
from app.models.responses import TriageResponse
from app.db.repositories import TriageRepository, IdempotencyRepository
from app.db.fsm_repository import FSMTriageRepository
from app.db.schemas import TriageLogDocument, IdempotencyKeyDocument, RiskLevel
from app.engine.orchestrator import assess_maternal_risk
from app.engine.fsm_orchestrator import TriageStateMachine, FSMContext, FSMState
from app.engine.rules import ClinicalRulesEngine
from app.engine.ml_model import MaternalHealthPredictor
from app.engine.circuit import CircuitBreaker
from app.config import settings
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
    Submit maternal health triage assessment using FSM architecture.
    
    This endpoint uses a Finite State Machine for deterministic processing:
    INGEST → SANITY → RULE_ENGINE → ML_INFERENCE → CONFIDENCE_CHECK → SAVE_DB
    
    Terminal states:
    - DONE: Successfully assessed
    - REJECT: Validation/honeypot failure
    - HITL_HANDOFF: Low confidence, requires doctor review
    
    Args:
        request: Triage request with clinical vitals
        idempotency_key: Optional UUID for request deduplication
        current_user: Authenticated user
        database: Database connection
    
    Returns:
        Comprehensive risk assessment with FSM trace
    
    Headers:
        x-idempotency-key: UUID for request deduplication (optional)
        X-Idempotent-Replay: true (if cached response returned)
    """
    user_id = current_user["_id"]
    
    # Generate client_sync_uuid if not provided
    client_sync_uuid = idempotency_key or str(uuid.uuid4())
    
    logger.info(
        f"Triage request received for user: {user_id}",
        extra={"client_sync_uuid": client_sync_uuid}
    )
    
    # =========================================================================
    # IDEMPOTENCY CHECK (FSM-based)
    # =========================================================================
    fsm_repo = FSMTriageRepository(database)
    
    cached_decision = await fsm_repo.check_idempotency(
        client_sync_uuid=client_sync_uuid,
        ttl_minutes=10
    )
    
    if cached_decision:
        logger.info(
            f"Idempotency cache HIT: {client_sync_uuid}",
            extra={"user_id": user_id}
        )
        response.headers["X-Idempotent-Replay"] = "true"
        
        # Return cached response
        return TriageResponse(
            assessment_id=str(cached_decision["_id"]),
            risk_level=cached_decision["final_risk_level"],
            confidence=cached_decision["confidence"],
            alerts=cached_decision["alerts"],
            clinical_notes=cached_decision.get("clinical_notes", []),
            feature_importances={},
            engine_source=cached_decision["engine_source"],
            fallback_active=False,
            timestamp=cached_decision["created_at"],
            processing_time_ms=int(cached_decision["processing_time_ms"]),
            fsm_trace=cached_decision.get("fsm_trace", []),
            requires_hitl=cached_decision.get("requires_hitl", False)
        )
    
    # =========================================================================
    # FSM EXECUTION
    # =========================================================================
    try:
        start_time = datetime.utcnow()
        
        # Extract patient name from symptoms field
        patient_name = None
        if request.vitals.symptoms and 'Patient:' in request.vitals.symptoms:
            patient_name = request.vitals.symptoms.split('|')[0].replace('Patient:', '').strip()
            logger.info(f"Extracted patient name: {patient_name}")
        
        # Initialize FSM context
        context = FSMContext(
            raw_vitals=request.vitals.model_dump(),
            user_id=user_id,
            client_sync_uuid=client_sync_uuid
        )
        
        # Initialize FSM orchestrator
        rules_engine = ClinicalRulesEngine()
        ml_model = MaternalHealthPredictor()
        circuit_breaker = CircuitBreaker(
            failure_threshold=getattr(settings, 'circuit_breaker_threshold', 5),
            timeout_seconds=getattr(settings, 'circuit_breaker_timeout', 60)
        )
        
        fsm = TriageStateMachine(
            rules_engine=rules_engine,
            ml_model=ml_model,
            circuit_breaker=circuit_breaker
        )
        
        # Execute FSM
        context = await fsm.execute(context)
        
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        # =====================================================================
        # HANDLE TERMINAL STATES
        # =====================================================================
        
        if context.current_state == FSMState.REJECT:
            # Validation or honeypot failure
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=context.error_message or "Request rejected by validation"
            )
        
        elif context.current_state == FSMState.HITL_HANDOFF:
            # Low confidence - requires human review
            decision_data = {
                "client_sync_uuid": client_sync_uuid,
                "user_id": user_id,
                "patient_uuid": patient_name,  # Use patient_name as UUID for now
                "patient_name": patient_name,
                "input_vitals": context.raw_vitals,
                "fsm_state": context.current_state,
                "final_risk_level": context.final_risk_level,
                "confidence": context.confidence,
                "alerts": context.alerts,
                "clinical_notes": ["Low confidence - requires HITL review"],
                "fsm_trace": [t.model_dump() for t in context.fsm_trace],
                "is_honeypot_triggered": context.is_honeypot_triggered,
                "bypassed_ml": context.bypass_ml,
                "requires_hitl": True,
                "review_status": "PENDING",
                "version_id": 1,
                "engine_source": "FSM_HITL",
                "processing_time_ms": processing_time,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            decision_id = await fsm_repo.save_triage_decision(decision_data)
            
            logger.info(f"HITL case created: {decision_id}")
            
            return TriageResponse(
                assessment_id=decision_id,
                risk_level=context.final_risk_level or "MEDIUM",
                confidence=context.confidence or 0.5,
                alerts=context.alerts + ["⏳ Pending doctor review"],
                clinical_notes=["Low confidence assessment - awaiting HITL review"],
                feature_importances={},
                engine_source="FSM_HITL",
                fallback_active=False,
                timestamp=datetime.utcnow(),
                processing_time_ms=int(processing_time),
                fsm_trace=fsm.get_trace_summary(context),
                requires_hitl=True
            )
        
        elif context.current_state == FSMState.DONE:
            # Success - save decision
            decision_data = {
                "client_sync_uuid": client_sync_uuid,
                "user_id": user_id,
                "patient_uuid": patient_name,
                "patient_name": patient_name,
                "input_vitals": context.raw_vitals,
                "fsm_state": context.current_state,
                "final_risk_level": context.final_risk_level,
                "confidence": context.confidence,
                "alerts": context.alerts,
                "clinical_notes": [],
                "fsm_trace": [t.model_dump() for t in context.fsm_trace],
                "is_honeypot_triggered": context.is_honeypot_triggered,
                "bypassed_ml": context.bypass_ml,
                "requires_hitl": False,
                "review_status": "PENDING",
                "version_id": 1,
                "engine_source": "FSM",
                "processing_time_ms": processing_time,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            decision_id = await fsm_repo.save_triage_decision(decision_data)
            
            logger.info(
                f"Triage assessment completed: {context.final_risk_level}",
                extra={"user_id": user_id, "decision_id": decision_id}
            )
            
            return TriageResponse(
                assessment_id=decision_id,
                risk_level=context.final_risk_level,
                confidence=context.confidence,
                alerts=context.alerts,
                clinical_notes=[],
                feature_importances=context.ml_result.get("feature_importances", {}) if context.ml_result else {},
                engine_source="FSM",
                fallback_active=False,
                timestamp=datetime.utcnow(),
                processing_time_ms=int(processing_time),
                fsm_trace=fsm.get_trace_summary(context),
                requires_hitl=False
            )
        
        else:
            # Unexpected state
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Unexpected FSM state: {context.current_state}"
            )
    
    except HTTPException:
        raise
    
    except ValueError as e:
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
