"""
Vitals Form Component
Reusable form for clinical data entry
"""

import streamlit as st
from typing import Dict, Optional

def show_vitals_form() -> Optional[Dict]:
    """
    Display vitals input form with validation
    
    Returns:
        Dict with vitals data if form is valid, None otherwise
    """
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 👤 Personal Information")
        age = st.number_input(
            "Age (years)",
            min_value=15,
            max_value=60,
            value=28,
            help="Age must be between 15-60 years"
        )
        
        gestational_weeks = st.number_input(
            "Gestational Weeks",
            min_value=1,
            max_value=42,
            value=20,
            help="Current week of pregnancy (1-42)"
        )
        
        st.markdown("### 🫀 Cardiovascular")
        systolic_bp = st.number_input(
            "Systolic Blood Pressure (mmHg)",
            min_value=70,
            max_value=230,
            value=120,
            help="Top number in blood pressure reading"
        )
        
        diastolic_bp = st.number_input(
            "Diastolic Blood Pressure (mmHg)",
            min_value=40,
            max_value=140,
            value=80,
            help="Bottom number in blood pressure reading"
        )
        
        # Validation: systolic must be > diastolic
        if systolic_bp <= diastolic_bp:
            st.error("⚠️ Systolic BP must be GREATER than Diastolic BP")
        
        heart_rate = st.number_input(
            "Heart Rate (bpm)",
            min_value=45,
            max_value=180,
            value=75,
            help="Resting heart rate in beats per minute"
        )
    
    with col2:
        st.markdown("### 🌡️ Metabolic")
        body_temperature = st.number_input(
            "Body Temperature (°C)",
            min_value=34.0,
            max_value=42.0,
            value=37.0,
            step=0.1,
            format="%.1f",
            help="Normal range: 36.5-37.5°C"
        )
        
        blood_oxygen = st.number_input(
            "Blood Oxygen Saturation (%)",
            min_value=70,
            max_value=100,
            value=98,
            help="SpO2 percentage (normal: >95%)"
        )
        
        blood_sugar = st.number_input(
            "Blood Sugar (mmol/L)",
            min_value=0.5,
            max_value=30.0,
            value=5.0,
            step=0.1,
            format="%.1f",
            help="Fasting: 3.9-5.5 mmol/L, After meal: <7.8 mmol/L"
        )
        
        st.markdown("### 📝 Notes")
        symptoms = st.text_area(
            "Current Symptoms (optional)",
            placeholder="Any symptoms you're experiencing...",
            help="Describe any symptoms like headache, dizziness, nausea, etc."
        )
    
    # Validation warnings
    warnings = []
    
    if systolic_bp >= 140 or diastolic_bp >= 90:
        warnings.append("⚠️ High blood pressure detected - CRITICAL THRESHOLD")
    
    if blood_oxygen < 94:
        warnings.append("⚠️ Low oxygen saturation - Hypoxia risk")
    
    if heart_rate > 120:
        warnings.append("⚠️ Elevated heart rate - Tachycardia")
    
    if body_temperature > 38.5:
        warnings.append("⚠️ High temperature - Possible infection")
    
    if blood_sugar < 3.0:
        warnings.append("⚠️ Low blood sugar - Hypoglycemia risk")
    elif blood_sugar > 11.0:
        warnings.append("⚠️ High blood sugar - Hyperglycemia risk")
    
    if age >= 35:
        warnings.append("ℹ️ Advanced maternal age - Additional monitoring recommended")
    
    if gestational_weeks > 40:
        warnings.append("ℹ️ Post-term pregnancy - Consult healthcare provider")
    
    if warnings:
        st.warning("**Pre-Assessment Warnings:**\n" + "\n".join(warnings))
    
    # Return vitals data if valid
    if systolic_bp > diastolic_bp:
        vitals_data = {
            "age": age,
            "systolic_bp": systolic_bp,
            "diastolic_bp": diastolic_bp,
            "blood_sugar": blood_sugar,
            "body_temp": body_temperature,
            "heart_rate": heart_rate,
            "blood_oxygen": blood_oxygen,
            "gestational_weeks": gestational_weeks
        }
        
        if symptoms:
            vitals_data["symptoms"] = symptoms
        
        return vitals_data
    
    return None
