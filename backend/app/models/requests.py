"""
API Request Models - DTOs for Incoming Requests
================================================
"""

from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field
from app.engine.sanity import ClinicalVitals


class LoginRequest(BaseModel):
    """Login request payload."""
    email: EmailStr
    password: str = Field(..., min_length=6)
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "sarah@example.com",
                "password": "SecurePass123"
            }
        }


class RegisterRequest(BaseModel):
    """User registration request."""
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: str = Field(..., min_length=2, max_length=100)
    role: str = Field(..., pattern="^(asha|doctor)$")
    
    # Security: Invite code required for doctor role
    invite_code: Optional[str] = Field(None, description="Required for doctor role registration")
    
    # Optional fields
    age: Optional[int] = Field(None, ge=15, le=100)
    phone: Optional[str] = None
    
    # ASHA-specific
    gestational_weeks: Optional[int] = Field(None, ge=1, le=42)
    pre_existing_conditions: List[str] = Field(default_factory=list)
    
    # Doctor-specific
    specialization: Optional[str] = None
    license_number: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "sarah@example.com",
                "password": "SecurePass123",
                "full_name": "Sarah Johnson",
                "role": "asha",
                "age": 28,
                "gestational_weeks": 24,
                "pre_existing_conditions": ["gestational_diabetes"]
            }
        }


class TriageRequest(BaseModel):
    """Triage assessment request."""
    vitals: ClinicalVitals
    notes: Optional[str] = Field(None, max_length=500)
    
    class Config:
        json_schema_extra = {
            "example": {
                "vitals": {
                    "age": 28,
                    "systolic_bp": 145,
                    "diastolic_bp": 95,
                    "heart_rate": 88,
                    "body_temp": 37.2,
                    "blood_oxygen": 97,
                    "blood_sugar": 6.5,
                    "gestational_weeks": 28
                },
                "notes": "Feeling slightly dizzy"
            }
        }


class ProfileUpdateRequest(BaseModel):
    """Profile update request."""
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    age: Optional[int] = Field(None, ge=15, le=100)
    phone: Optional[str] = None
    gestational_weeks: Optional[int] = Field(None, ge=1, le=42)
    pre_existing_conditions: Optional[List[str]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "full_name": "Sarah Johnson",
                "age": 29,
                "gestational_weeks": 32,
                "pre_existing_conditions": ["gestational_diabetes", "anemia"]
            }
        }
