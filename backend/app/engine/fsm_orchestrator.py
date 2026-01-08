"""
FSM Orchestrator - Finite State Machine for Triage Processing
==============================================================
Wraps existing validation, rules, and ML layers in a deterministic state machine
for traceability, idempotency, and Human-in-the-Loop integration.

States:
- INGEST: Entry point, honeypot detection
- SANITY: Pydantic validation (existing ClinicalVitals)
- RULE_ENGINE: Clinical rules (existing ClinicalRulesEngine)
- ML_INFERENCE: ML prediction via circuit breaker
- CONFIDENCE_CHECK: Determine if HITL needed
- SAVE_DB: Persist decision with idempotency
- DONE: Terminal success state
- REJECT: Terminal failure state
- HITL_HANDOFF: Terminal state for human review
"""

from enum import Enum
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from pydantic import BaseModel
from app.engine.sanity import ClinicalVitals
from app.engine.rules import ClinicalRulesEngine
from app.engine.ml_model import MaternalHealthPredictor
from app.engine.circuit import CircuitBreaker
from app.config import settings
from app.utils.logger import logger


class FSMState(str, Enum):
    """Finite State Machine states for triage processing."""
    INGEST = "INGEST"
    SANITY = "SANITY"
    RULE_ENGINE = "RULE_ENGINE"
    ML_INFERENCE = "ML_INFERENCE"
    CONFIDENCE_CHECK = "CONFIDENCE_CHECK"
    SAVE_DB = "SAVE_DB"
    DONE = "DONE"
    REJECT = "REJECT"
    HITL_HANDOFF = "HITL_HANDOFF"


class FSMTransition(BaseModel):
    """Record of a single state transition."""
    from_state: FSMState
    to_state: FSMState
    timestamp: datetime
    duration_ms: float
    metadata: Dict[str, Any] = {}


class FSMContext(BaseModel):
    """Execution context passed between FSM states."""
    # Input
    raw_vitals: Dict[str, Any]
    user_id: str
    client_sync_uuid: Optional[str] = None
    
    # Processing artifacts
    validated_vitals: Optional[ClinicalVitals] = None
    rule_result: Optional[Dict[str, Any]] = None
    ml_result: Optional[Dict[str, Any]] = None
    final_risk_level: Optional[str] = None
    confidence: Optional[float] = None
    alerts: List[str] = []
    
    # FSM tracking
    current_state: FSMState = FSMState.INGEST
    fsm_trace: List[FSMTransition] = []
    is_honeypot_triggered: bool = False
    bypass_ml: bool = False
    requires_hitl: bool = False
    error_message: Optional[str] = None
    
    class Config:
        arbitrary_types_allowed = True


class TriageStateMachine:
    """
    Finite State Machine orchestrator for triage processing.
    
    Wraps existing layers (Pydantic, Rules, ML) in a deterministic flow
    with observability, idempotency, and HITL integration.
    """
    
    def __init__(
        self,
        rules_engine: ClinicalRulesEngine,
        ml_model: MaternalHealthPredictor,
        circuit_breaker: CircuitBreaker
    ):
        self.rules_engine = rules_engine
        self.ml_model = ml_model
        self.circuit_breaker = circuit_breaker
        self.hitl_threshold = getattr(settings, 'hitl_confidence_threshold', 0.65)
    
    async def execute(self, context: FSMContext) -> FSMContext:
        """
        Execute the FSM from INGEST to terminal state.
        
        Args:
            context: Initial execution context
        
        Returns:
            Updated context with FSM trace and results
        """
        logger.info(f"FSM execution started for user: {context.user_id}")
        
        while context.current_state not in [FSMState.DONE, FSMState.REJECT, FSMState.HITL_HANDOFF]:
            state_start = datetime.utcnow()
            previous_state = context.current_state
            
            try:
                # Execute current state
                if context.current_state == FSMState.INGEST:
                    context = await self._state_ingest(context)
                elif context.current_state == FSMState.SANITY:
                    context = await self._state_sanity(context)
                elif context.current_state == FSMState.RULE_ENGINE:
                    context = await self._state_rule_engine(context)
                elif context.current_state == FSMState.ML_INFERENCE:
                    context = await self._state_ml_inference(context)
                elif context.current_state == FSMState.CONFIDENCE_CHECK:
                    context = await self._state_confidence_check(context)
                elif context.current_state == FSMState.SAVE_DB:
                    context = await self._state_save_db(context)
                
                # Record transition
                duration = (datetime.utcnow() - state_start).total_seconds() * 1000
                transition = FSMTransition(
                    from_state=previous_state,
                    to_state=context.current_state,
                    timestamp=datetime.utcnow(),
                    duration_ms=round(duration, 2),
                    metadata={"error": context.error_message} if context.error_message else {}
                )
                context.fsm_trace.append(transition)
                
            except Exception as e:
                logger.error(f"FSM state {context.current_state} failed: {str(e)}")
                context.error_message = str(e)
                context.current_state = FSMState.REJECT
                
                # Record failure transition
                duration = (datetime.utcnow() - state_start).total_seconds() * 1000
                transition = FSMTransition(
                    from_state=previous_state,
                    to_state=FSMState.REJECT,
                    timestamp=datetime.utcnow(),
                    duration_ms=round(duration, 2),
                    metadata={"error": str(e)}
                )
                context.fsm_trace.append(transition)
        
        logger.info(
            f"FSM execution completed: {context.current_state} "
            f"({len(context.fsm_trace)} transitions)"
        )
        
        return context
    
    async def _state_ingest(self, context: FSMContext) -> FSMContext:
        """
        INGEST state: Entry point, honeypot detection.
        
        Checks for malicious fields that should never appear in legitimate requests.
        """
        honeypot_fields = ['admin_debug_mode', '__proto__', '__debug__', 'is_admin', 'debug_mode']
        
        for field in honeypot_fields:
            if field in context.raw_vitals:
                logger.warning(f"Honeypot triggered: {field} found in request")
                context.is_honeypot_triggered = True
                context.error_message = "Invalid request structure"
                context.current_state = FSMState.REJECT
                return context
        
        # Success - move to validation
        context.current_state = FSMState.SANITY
        return context
    
    async def _state_sanity(self, context: FSMContext) -> FSMContext:
        """
        SANITY state: Pydantic validation using existing ClinicalVitals.
        """
        try:
            context.validated_vitals = ClinicalVitals(**context.raw_vitals)
            context.current_state = FSMState.RULE_ENGINE
        except Exception as e:
            logger.error(f"Sanity check failed: {str(e)}")
            context.error_message = f"Validation failed: {str(e)}"
            context.current_state = FSMState.REJECT
        
        return context
    
    async def _state_rule_engine(self, context: FSMContext) -> FSMContext:
        """
        RULE_ENGINE state: Execute clinical rules using existing engine.
        """
        rule_result = self.rules_engine.evaluate(context.validated_vitals)
        context.rule_result = rule_result
        
        # Check if rules override ML
        if rule_result.get('bypass_ml', False):
            context.bypass_ml = True
            context.final_risk_level = rule_result['risk_level']
            context.confidence = 1.0  # Clinical rules are 100% confident
            context.alerts = rule_result.get('alerts', [])
            context.current_state = FSMState.CONFIDENCE_CHECK
        else:
            # Need ML inference
            context.current_state = FSMState.ML_INFERENCE
        
        return context
    
    async def _state_ml_inference(self, context: FSMContext) -> FSMContext:
        """
        ML_INFERENCE state: Execute ML model via circuit breaker.
        """
        try:
            # Call ML through circuit breaker
            ml_result = await self.circuit_breaker.call(
                self.ml_model.predict,
                context.validated_vitals
            )
            
            context.ml_result = ml_result
            context.final_risk_level = ml_result['risk_level']
            context.confidence = ml_result['confidence']
            context.alerts = ml_result.get('alerts', [])
            context.current_state = FSMState.CONFIDENCE_CHECK
            
        except Exception as e:
            logger.error(f"ML inference failed: {str(e)}")
            # Fallback to rule-based assessment
            context.final_risk_level = context.rule_result.get('risk_level', 'MEDIUM')
            context.confidence = 0.5
            context.alerts = ["ML model unavailable - using rule-based assessment"]
            context.current_state = FSMState.CONFIDENCE_CHECK
        
        return context
    
    async def _state_confidence_check(self, context: FSMContext) -> FSMContext:
        """
        CONFIDENCE_CHECK state: Determine if human review needed.
        
        Triggers HITL if:
        - Confidence below threshold (default 65%)
        - AND not bypassed by clinical rules
        """
        if not context.bypass_ml and context.confidence < self.hitl_threshold:
            logger.info(
                f"HITL triggered: confidence {context.confidence} < {self.hitl_threshold}"
            )
            context.requires_hitl = True
            context.current_state = FSMState.HITL_HANDOFF
        else:
            context.current_state = FSMState.SAVE_DB
        
        return context
    
    async def _state_save_db(self, context: FSMContext) -> FSMContext:
        """
        SAVE_DB state: Persist decision (handled by repository layer).
        
        This state marker indicates the decision is ready for persistence.
        Actual DB save happens in the repository to maintain separation.
        """
        context.current_state = FSMState.DONE
        return context
    
    def get_trace_summary(self, context: FSMContext) -> Dict[str, Any]:
        """
        Generate FSM trace summary for debugging and monitoring.
        
        Args:
            context: Completed FSM context
        
        Returns:
            Summary dict with state transitions and timings
        """
        return {
            "final_state": context.current_state,
            "total_transitions": len(context.fsm_trace),
            "total_duration_ms": sum(t.duration_ms for t in context.fsm_trace),
            "honeypot_triggered": context.is_honeypot_triggered,
            "bypassed_ml": context.bypass_ml,
            "requires_hitl": context.requires_hitl,
            "transitions": [
                {
                    "from": t.from_state,
                    "to": t.to_state,
                    "duration_ms": t.duration_ms,
                    "timestamp": t.timestamp.isoformat()
                }
                for t in context.fsm_trace
            ]
        }
