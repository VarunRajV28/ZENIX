"""
Database Schemas - Pydantic Models for MongoDB Documents
=========================================================
Defines data models for MongoDB collections with validation.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, EmailStr
from enum import Enum


class UserRole(str, Enum):
    """User role enumeration."""
    ASHA = "asha"
    DOCTOR = "doctor"
    ADMIN = "admin"


class RiskLevel(str, Enum):
    """Risk level classification."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class UserDocument(BaseModel):
    """
    User document schema.
    """
    email: EmailStr
    hashed_password: str
    full_name: str
    role: UserRole
    age: Optional[int] = None
    phone: Optional[str] = None
    
    # ASHA-specific fields
    working_weeks: Optional[int] = None
    due_date: Optional[datetime] = None
    pre_existing_conditions: List[str] = Field(default_factory=list)
    
    # Doctor-specific fields
    specialization: Optional[str] = None
    license_number: Optional[str] = None
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "sarah@example.com",
                "full_name": "Sarah Johnson",
                "role": "asha",
                "age": 28,
                "gestational_weeks": 24,
                "pre_existing_conditions": ["gestational_diabetes"]
            }
        }


class TriageLogDocument(BaseModel):
    """
    Triage assessment log document.
    """
    user_id: str
    patient_name: Optional[str] = None  # Name of the patient (for ASHA workers)
    
    # Input vitals
    age: int
    systolic_bp: int
    diastolic_bp: int
    blood_sugar: float
    body_temp: float
    heart_rate: int
    blood_oxygen: float
    gestational_weeks: int
    
    # Assessment results
    risk_level: RiskLevel
    confidence: float
    alerts: List[str]
    clinical_notes: List[str]
    feature_importances: Optional[Dict[str, float]] = None
    
    # Engine metadata
    engine_source: str  # "CLINICAL_RULES", "ML_MODEL", "HYBRID"
    fallback_active: bool = False

    
    # Processing metrics
    processing_time_ms: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "507f1f77bcf86cd799439011",
                "age": 32,
                "systolic_bp": 145,
                "diastolic_bp": 95,
                "blood_sugar": 6.5,
                "body_temp": 37.2,
                "heart_rate": 88,
                "blood_oxygen": 97,
                "gestational_weeks": 28,
                "risk_level": "HIGH",
                "confidence": 0.89,
                "alerts": ["HYPERTENSIVE_CRISIS"],
                "engine_source": "HYBRID"
            }
        }


class IdempotencyKeyDocument(BaseModel):
    """
    Idempotency key document for request deduplication.
    """
    idempotency_key: str
    user_id: str
    request_hash: str
    response_data: Dict[str, Any]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "idempotency_key": "550e8400-e29b-41d4-a716-446655440000",
                "user_id": "507f1f77bcf86cd799439011",
                "request_hash": "sha256_hash_here",
                "response_data": {"risk_level": "LOW"}
            }
        }


class ReviewStatus(str, Enum):
    """HITL review status enumeration."""
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    ESCALATED = "ESCALATED"
    DOWNGRADED = "DOWNGRADED"
    RESOLVED = "RESOLVED"


class TriageDecisionDocument(BaseModel):
    """
    FSM-based triage decision document with full audit trail.
    
    This collection stores FSM execution results with idempotency,
    versioning, and HITL support for Build2Break competition.
    """
    # Idempotency & Identity
    client_sync_uuid: str  # Unique per request (idempotency key)
    user_id: str  # ASHA worker who submitted
    patient_uuid: Optional[str] = None  # Unique patient identifier
    patient_name: Optional[str] = None
    
    # Input vitals (preserved for audit)
    input_vitals: Dict[str, Any]
    
    # FSM execution results
    fsm_state: str  # Final state: DONE, REJECT, HITL_HANDOFF
    final_risk_level: Optional[RiskLevel] = None
    confidence: Optional[float] = None
    alerts: List[str] = Field(default_factory=list)
    clinical_notes: List[str] = Field(default_factory=list)
    
    # FSM trace for debugging
    fsm_trace: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Defensive flags
    is_honeypot_triggered: bool = False
    bypassed_ml: bool = False
    
    # HITL integration
    requires_hitl: bool = False
    review_status: ReviewStatus = ReviewStatus.PENDING
    reviewed_by: Optional[str] = None  # Doctor user_id
    reviewed_at: Optional[datetime] = None
    review_notes: Optional[str] = None
    
    # Optimistic locking for concurrent updates
    version_id: int = 1
    
    # Engine metadata
    engine_source: str  # "CLINICAL_RULES", "ML_MODEL", "HYBRID", "FSM"
    processing_time_ms: float
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "client_sync_uuid": "550e8400-e29b-41d4-a716-446655440000",
                "user_id": "507f1f77bcf86cd799439011",
                "patient_uuid": "pat_abc123",
                "patient_name": "Jane Doe",
                "input_vitals": {"age": 28, "systolic_bp": 120},
                "fsm_state": "DONE",
                "final_risk_level": "LOW",
                "confidence": 0.92,
                "alerts": [],
                "fsm_trace": [{"from": "INGEST", "to": "SANITY", "duration_ms": 5}],
                "is_honeypot_triggered": False,
                "bypassed_ml": False,
                "requires_hitl": False,
                "review_status": "PENDING",
                "version_id": 1,
                "engine_source": "FSM",
                "processing_time_ms": 156.4
            }
        }


class HoneypotAlertDocument(BaseModel):
    """
    Honeypot trigger alert for security monitoring.
    
    Optional collection for tracking attack attempts.
    """
    triggered_field: str
    endpoint: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    request_payload: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "triggered_field": "admin_debug_mode",
                "endpoint": "/triage",
                "ip_address": "192.168.1.100",
                "user_agent": "Mozilla/5.0...",
                "request_payload": {"admin_debug_mode": True},
                "timestamp": "2026-01-08T12:00:00"
            }
        }

