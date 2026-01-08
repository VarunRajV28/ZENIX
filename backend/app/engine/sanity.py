"""
Layer 0: Adversarial Defense - Sanity Validation
=================================================
CRITICAL MISSION: Reject biologically impossible inputs BEFORE they reach
the database or ML model. This is the first line of defense against adversarial attacks.

Attack Scenarios Defended:
1. Negative values (age=-5, BP=-120/-80)
2. Extreme outliers (BP=999/999, HR=500)
3. Reversed blood pressure (systolic < diastolic)
4. Non-numeric string injection
5. NULL/None in required fields
6. Float overflow/underflow

Biological Constraints Enforced:
- Age: 15-60 years (reproductive age)
- Systolic BP: 70-230 mmHg (MUST be > diastolic)
- Diastolic BP: 40-140 mmHg
- Heart Rate: 45-180 bpm
- Body Temperature: 34-42°C
- Blood Oxygen: 70-100%
- Blood Sugar: 0.5-30 mmol/L
- Gestational Weeks: 1-42 weeks
"""

from typing import Optional
from pydantic import BaseModel, Field, field_validator, model_validator


class ClinicalVitals(BaseModel):
    """
    Validated clinical vitals with adversarial defense.
    
    All values are constrained to biologically plausible ranges.
    Custom validators ensure logical consistency (e.g., systolic > diastolic).
    """
    
    age: int = Field(
        ...,
        ge=15,
        le=60,
        description="Patient age in years (reproductive age range)"
    )
    
    systolic_bp: int = Field(
        ...,
        ge=70,
        le=230,
        description="Systolic blood pressure in mmHg"
    )
    
    diastolic_bp: int = Field(
        ...,
        ge=40,
        le=140,
        description="Diastolic blood pressure in mmHg"
    )
    
    heart_rate: int = Field(
        ...,
        ge=45,
        le=180,
        description="Heart rate in beats per minute"
    )
    
    body_temp: float = Field(
        ...,
        ge=34.0,
        le=42.0,
        description="Body temperature in Celsius"
    )
    
    blood_oxygen: float = Field(
        ...,
        ge=70.0,
        le=100.0,
        description="Blood oxygen saturation percentage"
    )
    
    blood_sugar: float = Field(
        ...,
        ge=0.5,
        le=30.0,
        description="Blood glucose in mmol/L"
    )
    
    gestational_weeks: int = Field(
        ...,
        ge=1,
        le=42,
        description="Gestational age in weeks"
    )
    
    @model_validator(mode='after')
    def validate_blood_pressure(self):
        """
        CRITICAL: Ensure systolic BP is greater than diastolic BP.
        This prevents reversed BP values (common adversarial attack).
        """
        if self.systolic_bp <= self.diastolic_bp:
            raise ValueError(
                f"ADVERSARIAL_INPUT: Systolic BP ({self.systolic_bp}) must be GREATER than "
                f"diastolic BP ({self.diastolic_bp}). "
                f"Biological constraint: Systolic > Diastolic. "
                f"This may be an attack or data entry error."
            )
        return self
    
    @field_validator('body_temp')
    @classmethod
    def validate_temperature(cls, v: float) -> float:
        """
        Accept all temperatures within biological range.
        Classification of dangerous ranges is handled by the rules engine.
        """
        # Just return the value - let rules engine classify the risk
        return v
    
    @field_validator('blood_oxygen')
    @classmethod
    def validate_oxygen(cls, v: float) -> float:
        """
        Accept all oxygen levels within biological range.
        Classification of dangerous ranges is handled by the rules engine.
        """
        # Just return the value - let rules engine classify the risk
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "age": 28,
                "systolic_bp": 120,
                "diastolic_bp": 80,
                "heart_rate": 75,
                "body_temp": 37.0,
                "blood_oxygen": 98.0,
                "blood_sugar": 5.5,
                "gestational_weeks": 24
            }
        }


def validate_vitals(vitals_data: dict) -> ClinicalVitals:
    """
    Validate clinical vitals with comprehensive error handling.
    
    Args:
        vitals_data: Dictionary of vital signs
    
    Returns:
        Validated ClinicalVitals object
    
    Raises:
        ValueError: If validation fails with detailed error message
    """
    try:
        return ClinicalVitals(**vitals_data)
    except ValueError as e:
        # Re-raise with enhanced error context
        raise ValueError(
            f"Adversarial Defense (Layer 0) REJECTED input: {str(e)}"
        ) from e
