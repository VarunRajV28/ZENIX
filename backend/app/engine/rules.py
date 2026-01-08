"""
Layer 1: WHO Clinical Rules Engine
===================================
Implements evidence-based medical thresholds that BYPASS the ML model
for critical cases. This ensures immediate flagging of life-threatening
conditions without ML model dependency.

Evidence-Based Thresholds (WHO Guidelines):
- Hypertensive Crisis: SBP ≥140 OR DBP ≥90 (preeclampsia)
- Hypoxia: O2 <94% (respiratory distress)
- Severe Tachycardia: HR >120 bpm (hemorrhage/infection)
- Severe Hypoglycemia: Blood sugar <3.0 mmol/L (seizure risk)
- Severe Hyperglycemia: Blood sugar >11.0 mmol/L (gestational diabetes crisis)

BYPASS_ML Flag: When True, these rules alone determine the outcome,
ensuring no dependency on ML model availability.
"""

from enum import Enum
from typing import List, Dict, Any
from app.engine.sanity import ClinicalVitals


class RiskLevel(str, Enum):
    """Risk level classification."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ClinicalAlert(str, Enum):
    """Clinical alert types based on WHO guidelines."""
    HYPERTENSIVE_CRISIS = "HYPERTENSIVE_CRISIS"
    HYPOXIA = "HYPOXIA"
    TACHYCARDIA = "TACHYCARDIA"
    HYPERTHERMIA = "HYPERTHERMIA"
    HYPOGLYCEMIA = "HYPOGLYCEMIA"
    HYPERGLYCEMIA = "HYPERGLYCEMIA"
    ADVANCED_MATERNAL_AGE = "ADVANCED_MATERNAL_AGE"
    POST_TERM_PREGNANCY = "POST_TERM_PREGNANCY"


class ClinicalRulesEngine:
    """
    WHO-based clinical rules engine for maternal health assessment.
    
    This engine implements evidence-based thresholds that can operate
    independently of the ML model, ensuring system resilience.
    """
    
    # Clinical thresholds (WHO guidelines)
    HYPERTENSION_SBP_THRESHOLD = 140
    HYPERTENSION_DBP_THRESHOLD = 90
    HYPOXIA_THRESHOLD = 94.0
    TACHYCARDIA_THRESHOLD = 120
    HYPERTHERMIA_THRESHOLD = 38.5
    HYPOGLYCEMIA_THRESHOLD = 3.0
    HYPERGLYCEMIA_THRESHOLD = 11.0
    ADVANCED_AGE_THRESHOLD = 35
    POST_TERM_THRESHOLD = 40
    
    def evaluate(self, vitals: ClinicalVitals) -> Dict[str, Any]:
        """
        Evaluate clinical vitals against WHO thresholds.
        
        Args:
            vitals: Validated clinical vitals
        
        Returns:
            Dictionary containing:
            - risk_level: RiskLevel enum
            - alerts: List of ClinicalAlert enums
            - clinical_notes: Human-readable explanations
            - bypass_ml: True if rules alone determine outcome
            - confidence: 1.0 for rule-based decisions (100% certain)
        """
        alerts: List[ClinicalAlert] = []
        clinical_notes: List[str] = []
        risk_level = RiskLevel.LOW
        bypass_ml = False
        
        # CRITICAL FLAGS (immediate ML bypass)
        
        # 1. Hypertensive Crisis (Preeclampsia Risk)
        if vitals.systolic_bp >= self.HYPERTENSION_SBP_THRESHOLD or \
           vitals.diastolic_bp >= self.HYPERTENSION_DBP_THRESHOLD:
            alerts.append(ClinicalAlert.HYPERTENSIVE_CRISIS)
            clinical_notes.append(
                f"⚠️ HYPERTENSIVE CRISIS: BP {vitals.systolic_bp}/{vitals.diastolic_bp} mmHg. "
                f"WHO preeclampsia threshold exceeded (≥140/90). "
                f"Risk of eclampsia, stroke, and placental abruption. "
                f"IMMEDIATE obstetric evaluation required."
            )
            risk_level = RiskLevel.CRITICAL
            bypass_ml = True
        
        # 2. Hypoxia (Respiratory Distress)
        if vitals.blood_oxygen < self.HYPOXIA_THRESHOLD:
            alerts.append(ClinicalAlert.HYPOXIA)
            clinical_notes.append(
                f"⚠️ HYPOXIA: Blood oxygen {vitals.blood_oxygen}% (<94% threshold). "
                f"Indicates respiratory distress or cardiovascular compromise. "
                f"May affect fetal oxygenation. IMMEDIATE medical intervention required."
            )
            risk_level = RiskLevel.CRITICAL
            bypass_ml = True
        
        # 3. Severe Tachycardia (Hemorrhage/Infection Indicator)
        if vitals.heart_rate > self.TACHYCARDIA_THRESHOLD:
            alerts.append(ClinicalAlert.TACHYCARDIA)
            clinical_notes.append(
                f"⚠️ SEVERE TACHYCARDIA: Heart rate {vitals.heart_rate} bpm (>120 threshold). "
                f"Potential indicators: postpartum hemorrhage, infection, dehydration. "
                f"URGENT medical assessment required."
            )
            if risk_level != RiskLevel.CRITICAL:
                risk_level = RiskLevel.CRITICAL
            bypass_ml = True
        
        # 4. Severe Hypoglycemia (Seizure Risk)
        if vitals.blood_sugar < self.HYPOGLYCEMIA_THRESHOLD:
            alerts.append(ClinicalAlert.HYPOGLYCEMIA)
            clinical_notes.append(
                f"⚠️ SEVERE HYPOGLYCEMIA: Blood sugar {vitals.blood_sugar} mmol/L (<3.0 threshold). "
                f"Risk of seizures, loss of consciousness, fetal distress. "
                f"IMMEDIATE glucose administration required."
            )
            risk_level = RiskLevel.CRITICAL
            bypass_ml = True
        
        # 5. Severe Hyperglycemia (Gestational Diabetes Crisis)
        if vitals.blood_sugar > self.HYPERGLYCEMIA_THRESHOLD:
            alerts.append(ClinicalAlert.HYPERGLYCEMIA)
            clinical_notes.append(
                f"⚠️ SEVERE HYPERGLYCEMIA: Blood sugar {vitals.blood_sugar} mmol/L (>11.0 threshold). "
                f"Gestational diabetes crisis. Risk of diabetic ketoacidosis, fetal macrosomia. "
                f"URGENT endocrine consultation required."
            )
            risk_level = RiskLevel.CRITICAL
            bypass_ml = True
        
        # HIGH RISK FLAGS (do not bypass ML, but flag as high priority)
        
        # 6. Hyperthermia (Infection Risk)
        if vitals.body_temp > self.HYPERTHERMIA_THRESHOLD:
            alerts.append(ClinicalAlert.HYPERTHERMIA)
            clinical_notes.append(
                f"⚠️ HYPERTHERMIA: Temperature {vitals.body_temp}°C (>38.5°C threshold). "
                f"Possible infection: chorioamnionitis, urinary tract infection, sepsis. "
                f"Requires immediate medical evaluation."
            )
            if risk_level == RiskLevel.LOW:
                risk_level = RiskLevel.HIGH
        
        # MEDIUM RISK FLAGS
        
        # 7. Advanced Maternal Age
        if vitals.age >= self.ADVANCED_AGE_THRESHOLD:
            alerts.append(ClinicalAlert.ADVANCED_MATERNAL_AGE)
            clinical_notes.append(
                f"📋 ADVANCED MATERNAL AGE: Age {vitals.age} years (≥35 threshold). "
                f"Increased risk: chromosomal abnormalities, gestational diabetes, preeclampsia. "
                f"Enhanced monitoring recommended."
            )
            if risk_level == RiskLevel.LOW:
                risk_level = RiskLevel.MEDIUM
        
        # 8. Post-term Pregnancy
        if vitals.gestational_weeks > self.POST_TERM_THRESHOLD:
            alerts.append(ClinicalAlert.POST_TERM_PREGNANCY)
            clinical_notes.append(
                f"📋 POST-TERM PREGNANCY: {vitals.gestational_weeks} weeks (>40 threshold). "
                f"Increased risk: stillbirth, meconium aspiration, macrosomia. "
                f"Consider induction of labor evaluation."
            )
            if risk_level == RiskLevel.LOW:
                risk_level = RiskLevel.MEDIUM
        
        # If no alerts, vitals are normal
        if not alerts:
            clinical_notes.append(
                "✅ All clinical parameters within normal ranges. "
                "Continue routine prenatal care and monitoring."
            )
        
        return {
            "risk_level": risk_level,
            "alerts": [alert.value for alert in alerts],
            "clinical_notes": clinical_notes,
            "bypass_ml": bypass_ml,
            "confidence": 1.0,  # 100% confidence in rule-based decisions
            "engine_source": "CLINICAL_RULES"
        }
