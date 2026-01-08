"""
Master Orchestrator - 3-Layer Risk Assessment Pipeline
=======================================================
Coordinates all risk assessment layers with fallback logic:

Layer 0 (Sanity): Pydantic validation (automatic via FastAPI)
Layer 1 (Rules): WHO clinical thresholds
Layer 2 (ML): RandomForest predictions (circuit-broken)
Layer 3 (Zudu AI): Enhanced insights (non-blocking)

Execution Flow:
1. Layer 1 evaluates clinical rules
2. If bypass_ml=True, return immediately with rule-based decision
3. Otherwise, attempt ML prediction through circuit breaker
4. On ML success: Merge ML + rules results
5. On ML failure: Use Layer 1 results with fallback_active=True
6. Zudu AI enhancement runs in background (3s timeout)
7. Return comprehensive assessment with all metadata

Defensive Engineering:
- System remains operational even if ML model or Zudu AI fail
- All failures are logged with context
- Processing time tracked for performance monitoring
"""

import time
import asyncio
from datetime import datetime
from typing import Dict, Any
from app.engine.sanity import ClinicalVitals
from app.engine.rules import ClinicalRulesEngine, RiskLevel
from app.engine.ml_model import predictor, MLModelException
from app.engine.circuit import circuit_breaker, CircuitBreakerOpen
from app.engine.zudu_integration import zudu_client
from app.utils.logger import logger


async def assess_maternal_risk(vitals: ClinicalVitals) -> Dict[str, Any]:
    """
    Comprehensive maternal risk assessment through 3-layer pipeline.
    
    Args:
        vitals: Validated clinical vitals
    
    Returns:
        Dictionary containing:
        - risk_level: Final RiskLevel
        - confidence: Prediction confidence
        - alerts: List of clinical alerts
        - clinical_notes: Human-readable explanations
        - feature_importances: ML feature importances (if available)
        - engine_source: "CLINICAL_RULES", "ML_MODEL", or "HYBRID"
        - fallback_active: True if ML model bypassed
        - zudu_insights: AI-enhanced insights (if available)
        - timestamp: Assessment timestamp
        - processing_time_ms: Processing duration
    """
    start_time = time.time()
    
    logger.info(
        "Starting maternal risk assessment",
        extra={
            "age": vitals.age,
            "gestational_weeks": vitals.gestational_weeks,
            "bp": f"{vitals.systolic_bp}/{vitals.diastolic_bp}"
        }
    )
    
    # =========================================================================
    # LAYER 1: WHO Clinical Rules Engine
    # =========================================================================
    rules_engine = ClinicalRulesEngine()
    rules_result = rules_engine.evaluate(vitals)
    
    logger.info(
        f"Layer 1 (Rules): {rules_result['risk_level']} - "
        f"Bypass ML: {rules_result['bypass_ml']}"
    )
    
    # Check if rules engine requires ML bypass (critical condition)
    if rules_result["bypass_ml"]:
        logger.warning(
            "CRITICAL CONDITION DETECTED: ML model bypassed by clinical rules"
        )
        
        # Try to get Zudu insights (non-blocking, best effort)
        zudu_insights = await _get_zudu_insights_safe(vitals, rules_result)
        
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        return {
            "risk_level": rules_result["risk_level"],
            "confidence": rules_result["confidence"],
            "alerts": rules_result["alerts"],
            "clinical_notes": rules_result["clinical_notes"],
            "feature_importances": {},
            "engine_source": "CLINICAL_RULES",
            "fallback_active": False,  # Not a fallback, intentional bypass
            "zudu_insights": zudu_insights,
            "timestamp": datetime.utcnow(),
            "processing_time_ms": processing_time_ms
        }
    
    # =========================================================================
    # LAYER 2: Machine Learning Model (Circuit-Protected)
    # =========================================================================
    ml_result = None
    fallback_active = False
    
    try:
        # Attempt ML prediction through circuit breaker
        ml_result = await circuit_breaker.call(
            _predict_with_ml,
            vitals
        )
        logger.info(f"Layer 2 (ML): {ml_result['risk_level']} (confidence: {ml_result['confidence']:.2f})")
    
    except CircuitBreakerOpen as e:
        logger.warning(f"Circuit breaker OPEN: {str(e)}")
        fallback_active = True
    
    except MLModelException as e:
        logger.error(f"ML model error: {str(e)}")
        fallback_active = True
    
    except Exception as e:
        logger.error(f"Unexpected ML error: {str(e)}", exc_info=True)
        fallback_active = True
    
    # =========================================================================
    # MERGE RESULTS: ML + Clinical Rules
    # =========================================================================
    if ml_result and not fallback_active:
        # HYBRID MODE: Merge ML predictions with clinical rule alerts
        final_result = _merge_ml_and_rules(ml_result, rules_result)
        engine_source = "HYBRID"
    else:
        # FALLBACK MODE: Use clinical rules only
        logger.warning("Using clinical rules fallback (ML unavailable)")
        final_result = rules_result
        final_result["feature_importances"] = {}
        engine_source = "CLINICAL_RULES"
    
    # =========================================================================
    # LAYER 3: Zudu AI Enhancement (Non-Blocking)
    # =========================================================================
    zudu_insights = await _get_zudu_insights_safe(vitals, final_result)
    
    # =========================================================================
    # FINAL RESPONSE
    # =========================================================================
    processing_time_ms = int((time.time() - start_time) * 1000)
    
    logger.info(
        f"Assessment complete: {final_result['risk_level']} "
        f"(engine: {engine_source}, time: {processing_time_ms}ms)"
    )
    
    return {
        "risk_level": final_result["risk_level"],
        "confidence": final_result.get("confidence", 1.0),
        "alerts": final_result["alerts"],
        "clinical_notes": final_result["clinical_notes"],
        "feature_importances": final_result.get("feature_importances", {}),
        "engine_source": engine_source,
        "fallback_active": fallback_active,
        "zudu_insights": zudu_insights,
        "timestamp": datetime.utcnow(),
        "processing_time_ms": processing_time_ms
    }


async def _predict_with_ml(vitals: ClinicalVitals) -> Dict[str, Any]:
    """
    Wrapper for ML prediction to work with async circuit breaker.
    
    Args:
        vitals: Clinical vitals
    
    Returns:
        ML prediction result
    """
    # Run CPU-bound ML prediction in executor to avoid blocking
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, predictor.predict, vitals)


def _merge_ml_and_rules(
    ml_result: Dict[str, Any],
    rules_result: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Merge ML predictions with clinical rules results.
    
    Strategy:
    - Use HIGHER risk level between ML and rules
    - Combine alerts from both sources
    - Use ML confidence if ML risk is higher
    - Merge clinical notes
    
    Args:
        ml_result: ML model prediction
        rules_result: Clinical rules assessment
    
    Returns:
        Merged assessment
    """
    # Risk level hierarchy
    risk_hierarchy = {
        RiskLevel.LOW: 0,
        RiskLevel.MEDIUM: 1,
        RiskLevel.HIGH: 2,
        RiskLevel.CRITICAL: 3
    }
    
    ml_risk_score = risk_hierarchy.get(ml_result["risk_level"], 0)
    rules_risk_score = risk_hierarchy.get(rules_result["risk_level"], 0)
    
    # Use higher risk level
    if ml_risk_score >= rules_risk_score:
        final_risk = ml_result["risk_level"]
        final_confidence = ml_result["confidence"]
    else:
        final_risk = rules_result["risk_level"]
        final_confidence = rules_result["confidence"]
    
    # Combine alerts (deduplicate)
    combined_alerts = list(set(
        ml_result.get("alerts", []) + rules_result.get("alerts", [])
    ))
    
    # Merge clinical notes
    combined_notes = rules_result.get("clinical_notes", []).copy()
    
    # Add ML insight note
    ml_risk_str = ml_result["risk_level"].value if hasattr(ml_result["risk_level"], "value") else str(ml_result["risk_level"])
    combined_notes.insert(0,
        f"🤖 ML Model Assessment: {ml_risk_str} "
        f"(confidence: {ml_result['confidence']:.1%})"
    )
    
    return {
        "risk_level": final_risk,
        "confidence": final_confidence,
        "alerts": combined_alerts,
        "clinical_notes": combined_notes,
        "feature_importances": ml_result.get("feature_importances", {})
    }


async def _get_zudu_insights_safe(
    vitals: ClinicalVitals,
    assessment: Dict[str, Any],
    timeout: int = 3
) -> Dict[str, Any]:
    """
    Get Zudu AI insights with timeout protection.
    
    Args:
        vitals: Clinical vitals
        assessment: Current assessment
        timeout: Timeout in seconds
    
    Returns:
        Zudu insights or None
    """
    try:
        # Run with timeout to prevent blocking
        zudu_insights = await asyncio.wait_for(
            zudu_client.analyze_clinical_context(vitals, assessment),
            timeout=timeout
        )
        return zudu_insights
    
    except asyncio.TimeoutError:
        logger.warning(f"Zudu AI timeout after {timeout}s")
        return None
    
    except Exception as e:
        logger.warning(f"Zudu AI error: {str(e)}")
        return None
