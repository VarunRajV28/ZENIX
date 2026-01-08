"""
Adversarial Input Defense Tests
Test Layer 0 validation against malicious and invalid inputs
"""

import pytest
from pydantic import ValidationError
from app.engine.sanity import ClinicalVitals

class TestAdversarialDefense:
    """Test suite for adversarial input scenarios"""
    
    def test_negative_age(self):
        """Test rejection of negative age"""
        with pytest.raises(ValidationError) as exc_info:
            ClinicalVitals(
                age=-5,
                systolic_bp=120,
                diastolic_bp=80,
                blood_sugar=5.0,
                body_temperature=37.0,
                heart_rate=75,
                blood_oxygen=98,
                gestational_weeks=20
            )
        
        errors = exc_info.value.errors()
        assert any('age' in str(e['loc']) for e in errors)
        assert 'greater than or equal to 15' in str(errors)
    
    def test_reversed_blood_pressure(self):
        """Test that systolic must be greater than diastolic"""
        with pytest.raises(ValidationError) as exc_info:
            ClinicalVitals(
                age=28,
                systolic_bp=110,
                diastolic_bp=130,  # Higher than systolic - INVALID
                blood_sugar=5.0,
                body_temperature=37.0,
                heart_rate=75,
                blood_oxygen=98,
                gestational_weeks=20
            )
        
        errors = exc_info.value.errors()
        assert 'systolic_bp must be greater than diastolic_bp' in str(errors)
    
    def test_extreme_outlier_heart_rate(self):
        """Test rejection of biologically impossible heart rate"""
        with pytest.raises(ValidationError) as exc_info:
            ClinicalVitals(
                age=28,
                systolic_bp=120,
                diastolic_bp=80,
                blood_sugar=5.0,
                body_temperature=37.0,
                heart_rate=500,  # Impossible value
                blood_oxygen=98,
                gestational_weeks=20
            )
        
        errors = exc_info.value.errors()
        assert any('heart_rate' in str(e['loc']) for e in errors)
    
    def test_bp_exceeds_maximum(self):
        """Test rejection of BP above biological limit"""
        with pytest.raises(ValidationError):
            ClinicalVitals(
                age=28,
                systolic_bp=999,  # Way too high
                diastolic_bp=999,
                blood_sugar=5.0,
                body_temperature=37.0,
                heart_rate=75,
                blood_oxygen=98,
                gestational_weeks=20
            )
    
    def test_blood_oxygen_below_minimum(self):
        """Test rejection of impossibly low oxygen saturation"""
        with pytest.raises(ValidationError):
            ClinicalVitals(
                age=28,
                systolic_bp=120,
                diastolic_bp=80,
                blood_sugar=5.0,
                body_temperature=37.0,
                heart_rate=75,
                blood_oxygen=50,  # Too low to sustain life
                gestational_weeks=20
            )
    
    def test_temperature_hypothermia(self):
        """Test flagging of hypothermia"""
        vitals = ClinicalVitals(
            age=28,
            systolic_bp=120,
            diastolic_bp=80,
            blood_sugar=5.0,
            body_temperature=34.5,  # Hypothermia
            heart_rate=75,
            blood_oxygen=98,
            gestational_weeks=20
        )
        
        assert vitals.body_temperature < 35.0  # Should still accept but flag
    
    def test_temperature_hyperthermia(self):
        """Test flagging of hyperthermia"""
        vitals = ClinicalVitals(
            age=28,
            systolic_bp=120,
            diastolic_bp=80,
            blood_sugar=5.0,
            body_temperature=40.5,  # High fever
            heart_rate=75,
            blood_oxygen=98,
            gestational_weeks=20
        )
        
        assert vitals.body_temperature > 40.0
    
    def test_gestational_weeks_out_of_range(self):
        """Test rejection of invalid gestational weeks"""
        with pytest.raises(ValidationError):
            ClinicalVitals(
                age=28,
                systolic_bp=120,
                diastolic_bp=80,
                blood_sugar=5.0,
                body_temperature=37.0,
                heart_rate=75,
                blood_oxygen=98,
                gestational_weeks=50  # Impossible - max 42 weeks
            )
    
    def test_blood_sugar_extreme_low(self):
        """Test rejection of impossibly low blood sugar"""
        with pytest.raises(ValidationError):
            ClinicalVitals(
                age=28,
                systolic_bp=120,
                diastolic_bp=80,
                blood_sugar=0.1,  # Too low
                body_temperature=37.0,
                heart_rate=75,
                blood_oxygen=98,
                gestational_weeks=20
            )
    
    def test_valid_vitals(self):
        """Test that valid vitals are accepted"""
        vitals = ClinicalVitals(
            age=28,
            systolic_bp=120,
            diastolic_bp=80,
            blood_sugar=5.0,
            body_temperature=37.0,
            heart_rate=75,
            blood_oxygen=98,
            gestational_weeks=20
        )
        
        assert vitals.age == 28
        assert vitals.systolic_bp == 120
        assert vitals.diastolic_bp == 80
    
    def test_boundary_values(self):
        """Test boundary values are accepted"""
        # Minimum values
        vitals_min = ClinicalVitals(
            age=15,
            systolic_bp=71,  # Just above minimum, must be > diastolic
            diastolic_bp=40,
            blood_sugar=0.5,
            body_temperature=34.0,
            heart_rate=45,
            blood_oxygen=70,
            gestational_weeks=1
        )
        assert vitals_min.age == 15
        
        # Maximum values
        vitals_max = ClinicalVitals(
            age=60,
            systolic_bp=230,
            diastolic_bp=140,
            blood_sugar=30.0,
            body_temperature=42.0,
            heart_rate=180,
            blood_oxygen=100,
            gestational_weeks=42
        )
        assert vitals_max.age == 60

    def test_type_validation(self):
        """Test that type validation works"""
        with pytest.raises(ValidationError):
            ClinicalVitals(
                age="twenty-eight",  # String instead of int
                systolic_bp=120,
                diastolic_bp=80,
                blood_sugar=5.0,
                body_temperature=37.0,
                heart_rate=75,
                blood_oxygen=98,
                gestational_weeks=20
            )
