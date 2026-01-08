"""
Clinical Rules Engine Tests
Test Layer 1 WHO clinical thresholds
"""

import pytest
from app.engine.sanity import ClinicalVitals
from app.engine.rules import ClinicalRulesEngine, RiskLevel, ClinicalAlert

class TestClinicalRules:
    """Test suite for clinical rules evaluation"""
    
    def setup_method(self):
        """Initialize rules engine before each test"""
        self.engine = ClinicalRulesEngine()
    
    def test_hypertensive_crisis_systolic(self):
        """Test CRITICAL flag for systolic BP >= 140"""
        vitals = ClinicalVitals(
            age=28,
            systolic_bp=145,
            diastolic_bp=85,
            blood_sugar=5.0,
            body_temperature=37.0,
            heart_rate=75,
            blood_oxygen=98,
            gestational_weeks=20
        )
        
        result = self.engine.evaluate(vitals)
        
        assert result['risk_level'] == RiskLevel.CRITICAL
        assert ClinicalAlert.HYPERTENSIVE_CRISIS in result['alerts']
        assert result['bypass_ml'] is True
        assert result['confidence'] == 1.0
    
    def test_hypertensive_crisis_diastolic(self):
        """Test CRITICAL flag for diastolic BP >= 90"""
        vitals = ClinicalVitals(
            age=28,
            systolic_bp=130,
            diastolic_bp=95,
            blood_sugar=5.0,
            body_temperature=37.0,
            heart_rate=75,
            blood_oxygen=98,
            gestational_weeks=20
        )
        
        result = self.engine.evaluate(vitals)
        
        assert result['risk_level'] == RiskLevel.CRITICAL
        assert ClinicalAlert.HYPERTENSIVE_CRISIS in result['alerts']
        assert result['bypass_ml'] is True
    
    def test_hypoxia_critical(self):
        """Test CRITICAL flag for oxygen saturation < 94%"""
        vitals = ClinicalVitals(
            age=28,
            systolic_bp=120,
            diastolic_bp=80,
            blood_sugar=5.0,
            body_temperature=37.0,
            heart_rate=75,
            blood_oxygen=92,  # Below threshold
            gestational_weeks=20
        )
        
        result = self.engine.evaluate(vitals)
        
        assert result['risk_level'] == RiskLevel.CRITICAL
        assert ClinicalAlert.HYPOXIA in result['alerts']
        assert result['bypass_ml'] is True
    
    def test_severe_tachycardia(self):
        """Test CRITICAL flag for heart rate > 120 bpm"""
        vitals = ClinicalVitals(
            age=28,
            systolic_bp=120,
            diastolic_bp=80,
            blood_sugar=5.0,
            body_temperature=37.0,
            heart_rate=125,
            blood_oxygen=98,
            gestational_weeks=20
        )
        
        result = self.engine.evaluate(vitals)
        
        assert result['risk_level'] == RiskLevel.CRITICAL
        assert ClinicalAlert.TACHYCARDIA in result['alerts']
    
    def test_severe_hypoglycemia(self):
        """Test CRITICAL flag for blood sugar < 3.0 mmol/L"""
        vitals = ClinicalVitals(
            age=28,
            systolic_bp=120,
            diastolic_bp=80,
            blood_sugar=2.5,  # Dangerously low
            body_temperature=37.0,
            heart_rate=75,
            blood_oxygen=98,
            gestational_weeks=20
        )
        
        result = self.engine.evaluate(vitals)
        
        assert result['risk_level'] == RiskLevel.CRITICAL
        assert ClinicalAlert.HYPOGLYCEMIA in result['alerts']
    
    def test_severe_hyperglycemia(self):
        """Test CRITICAL flag for blood sugar > 11.0 mmol/L"""
        vitals = ClinicalVitals(
            age=28,
            systolic_bp=120,
            diastolic_bp=80,
            blood_sugar=12.5,  # Very high
            body_temperature=37.0,
            heart_rate=75,
            blood_oxygen=98,
            gestational_weeks=20
        )
        
        result = self.engine.evaluate(vitals)
        
        assert result['risk_level'] == RiskLevel.CRITICAL
        assert ClinicalAlert.HYPERGLYCEMIA in result['alerts']
    
    def test_hyperthermia_high_risk(self):
        """Test HIGH risk for temperature > 38.5°C"""
        vitals = ClinicalVitals(
            age=28,
            systolic_bp=120,
            diastolic_bp=80,
            blood_sugar=5.0,
            body_temperature=39.0,  # Fever
            heart_rate=75,
            blood_oxygen=98,
            gestational_weeks=20
        )
        
        result = self.engine.evaluate(vitals)
        
        assert result['risk_level'] == RiskLevel.HIGH
        assert ClinicalAlert.HYPERTHERMIA in result['alerts']
    
    def test_advanced_maternal_age(self):
        """Test MEDIUM risk for age >= 35"""
        vitals = ClinicalVitals(
            age=37,  # Advanced maternal age
            systolic_bp=120,
            diastolic_bp=80,
            blood_sugar=5.0,
            body_temperature=37.0,
            heart_rate=75,
            blood_oxygen=98,
            gestational_weeks=20
        )
        
        result = self.engine.evaluate(vitals)
        
        assert result['risk_level'] in [RiskLevel.MEDIUM, RiskLevel.HIGH]
        assert ClinicalAlert.ADVANCED_MATERNAL_AGE in result['alerts']
    
    def test_post_term_pregnancy(self):
        """Test MEDIUM risk for gestational weeks > 40"""
        vitals = ClinicalVitals(
            age=28,
            systolic_bp=120,
            diastolic_bp=80,
            blood_sugar=5.0,
            body_temperature=37.0,
            heart_rate=75,
            blood_oxygen=98,
            gestational_weeks=41  # Post-term
        )
        
        result = self.engine.evaluate(vitals)
        
        assert result['risk_level'] in [RiskLevel.MEDIUM, RiskLevel.HIGH]
        assert ClinicalAlert.POST_TERM_PREGNANCY in result['alerts']
    
    def test_low_risk_healthy_patient(self):
        """Test LOW risk for completely healthy vitals"""
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
        
        result = self.engine.evaluate(vitals)
        
        assert result['risk_level'] == RiskLevel.LOW
        assert len(result['alerts']) == 0
        assert result['bypass_ml'] is False  # Should use ML for low-risk cases
    
    def test_multiple_critical_flags(self):
        """Test multiple CRITICAL conditions simultaneously"""
        vitals = ClinicalVitals(
            age=28,
            systolic_bp=155,  # Hypertensive crisis
            diastolic_bp=95,  # Also hypertensive
            blood_sugar=5.0,
            body_temperature=37.0,
            heart_rate=130,  # Tachycardia
            blood_oxygen=91,  # Hypoxia
            gestational_weeks=20
        )
        
        result = self.engine.evaluate(vitals)
        
        assert result['risk_level'] == RiskLevel.CRITICAL
        assert ClinicalAlert.HYPERTENSIVE_CRISIS in result['alerts']
        assert ClinicalAlert.TACHYCARDIA in result['alerts']
        assert ClinicalAlert.HYPOXIA in result['alerts']
        assert len(result['alerts']) >= 3
    
    def test_clinical_notes_generated(self):
        """Test that clinical notes are generated for alerts"""
        vitals = ClinicalVitals(
            age=28,
            systolic_bp=145,
            diastolic_bp=85,
            blood_sugar=5.0,
            body_temperature=37.0,
            heart_rate=75,
            blood_oxygen=98,
            gestational_weeks=20
        )
        
        result = self.engine.evaluate(vitals)
        
        assert len(result['clinical_notes']) > 0
        assert any('blood pressure' in note.lower() for note in result['clinical_notes'])
