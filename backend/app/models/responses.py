"""
API Response Models - DTOs for Outgoing Responses
==================================================
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class TokenResponse(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: str
    role: str
    full_name: str


class TriageResponse(BaseModel):
    """Triage assessment response."""
    assessment_id: str
    risk_level: str
    confidence: float
    alerts: List[str]
    clinical_notes: List[str]
    feature_importances: Dict[str, float]
    engine_source: str
    fallback_active: bool

    timestamp: datetime
    processing_time_ms: int
    
    # FSM additions
    fsm_trace: Optional[Dict[str, Any]] = None
    requires_hitl: bool = False
    
    class Config:
        json_schema_extra = {
            "example": {
                "assessment_id": "507f1f77bcf86cd799439011",
                "risk_level": "HIGH",
                "confidence": 0.89,
                "alerts": ["HYPERTENSIVE_CRISIS"],
                "clinical_notes": [
                    "⚠️ HYPERTENSIVE CRISIS: BP 145/95 mmHg..."
                ],
                "feature_importances": {
                    "systolic_bp": 0.35,
                    "age": 0.22,
                    "blood_sugar": 0.15
                },
                "engine_source": "HYBRID",
                "fallback_active": False,
                "processing_time_ms": 234,
                "fsm_trace": {
                    "final_state": "DONE",
                    "total_transitions": 6
                },
                "requires_hitl": False
            }
        }


class EmergencyAlert(BaseModel):
    """Emergency patient alert."""
    patient_id: str
    patient_name: str
    age: int
    gestational_weeks: int
    risk_level: str
    alerts: List[str]
    vitals_snapshot: Dict[str, Any]
    assessment_time: datetime
    hours_since_assessment: float
    
    class Config:
        json_schema_extra = {
            "example": {
                "patient_id": "507f1f77bcf86cd799439011",
                "patient_name": "Patient #12345",
                "age": 32,
                "gestational_weeks": 28,
                "risk_level": "CRITICAL",
                "alerts": ["HYPERTENSIVE_CRISIS", "TACHYCARDIA"],
                "vitals_snapshot": {
                    "bp": "145/95",
                    "heart_rate": 125,
                    "blood_oxygen": 96
                },
                "assessment_time": "2026-01-08T10:30:00",
                "hours_since_assessment": 2.5
            }
        }


class PriorityPatient(BaseModel):
    """Priority patient for triage list."""
    patient_id: str
    patient_name: str
    age: int
    gestational_weeks: int
    risk_level: str
    priority_score: float
    last_assessment: datetime
    hours_since_checkup: float
    alerts: List[str]
    
    class Config:
        json_schema_extra = {
            "example": {
                "patient_id": "507f1f77bcf86cd799439011",
                "patient_name": "Patient #12345",
                "age": 35,
                "gestational_weeks": 36,
                "risk_level": "HIGH",
                "priority_score": 8.5,
                "last_assessment": "2026-01-08T08:00:00",
                "hours_since_checkup": 4.5,
                "alerts": ["ADVANCED_MATERNAL_AGE"]
            }
        }


class DashboardData(BaseModel):
    """Doctor dashboard data."""
    emergency_alerts: List[EmergencyAlert]
    priority_patients: List[PriorityPatient]
    total_patients: int
    critical_count: int
    high_risk_count: int


class PatientProfile(BaseModel):
    """Patient profile information."""
    user_id: str
    full_name: str
    email: str
    age: Optional[int] = None
    phone: Optional[str] = None
    gestational_weeks: Optional[int] = None
    due_date: Optional[datetime] = None
    pre_existing_conditions: List[str] = Field(default_factory=list)
    created_at: datetime
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "507f1f77bcf86cd799439011",
                "full_name": "Sarah Johnson",
                "email": "sarah@example.com",
                "age": 28,
                "gestational_weeks": 24,
                "pre_existing_conditions": ["gestational_diabetes"]
            }
        }


class HistoryEntry(BaseModel):
    """Single history entry."""
    assessment_id: str
    timestamp: datetime
    risk_level: str
    confidence: float
    alerts: List[str]
    vitals: Dict[str, Any]


class HealthPassport(BaseModel):
    """Health passport summary."""
    patient_profile: PatientProfile
    assessment_history: List[HistoryEntry]
    risk_trend: Dict[str, Any]
    vitals_trends: Dict[str, List[Dict[str, Any]]]
    generated_at: datetime


class SystemHealth(BaseModel):
    """System health status."""
    status: str
    database_connected: bool
    ml_model_loaded: bool
    circuit_breaker_state: str
    fsm_statistics: Dict[str, Any]
    timestamp: datetime
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "database_connected": True,
                "ml_model_loaded": True,
                "circuit_breaker_state": "CLOSED",
                "fsm_statistics": {
                    "total_decisions": 150,
                    "honeypot_triggers": 3,
                    "hitl_cases": {"pending": 5, "resolved": 12}
                },
                "timestamp": "2026-01-08T10:30:00"
            }
        }


class SystemMetrics(BaseModel):
    """System performance metrics."""
    circuit_breaker: Dict[str, Any]
    database_status: Dict[str, Any]
    request_metrics: Dict[str, Any]
    timestamp: datetime
