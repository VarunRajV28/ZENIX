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
    MOTHER = "mother"
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
    
    # Mother-specific fields
    gestational_weeks: Optional[int] = None
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
                "role": "mother",
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
    zudu_insights: Optional[Dict[str, Any]] = None
    
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
