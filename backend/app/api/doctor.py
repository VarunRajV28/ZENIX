"""
Doctor API Endpoints
====================
Endpoints for doctor dashboard and patient management.

Endpoints:
- GET /dashboard/emergency: Critical patients in last 24 hours
- GET /patients/priority: Priority-sorted patient list
- GET /patients/{patient_id}/details: Patient history and details
"""

from datetime import datetime, timedelta
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.models.responses import EmergencyAlert, PriorityPatient, DashboardData, HistoryEntry
from app.db.repositories import TriageRepository, UserRepository
from app.utils.dependencies import get_database, get_current_doctor
from app.utils.logger import logger


router = APIRouter(prefix="/doctor", tags=["Doctor"])


@router.get("/dashboard/emergency", response_model=List[EmergencyAlert])
async def get_emergency_feed(
    current_user: dict = Depends(get_current_doctor),
    database: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get all CRITICAL patients from last 24 hours.
    
    Returns:
        List of emergency alerts sorted by timestamp (most recent first)
    """
    triage_repo = TriageRepository(database)
    user_repo = UserRepository(database)
    
    # Get critical patients
    critical_patients = await triage_repo.get_critical_patients(hours=24)
    
    alerts = []
    for record in critical_patients:
        # Get patient details
        patient = await user_repo.get_user_by_id(record["user_id"])
        if not patient:
            continue
        
        # Calculate hours since assessment
        hours_since = (datetime.utcnow() - record["timestamp"]).total_seconds() / 3600
        
        alert = EmergencyAlert(
            patient_id=record["user_id"],
            patient_name=f"Patient #{record['user_id'][-6:]}",  # Anonymized
            age=record["age"],
            gestational_weeks=record["gestational_weeks"],
            risk_level=record["risk_level"],
            alerts=record["alerts"],
            vitals_snapshot={
                "bp": f"{record['systolic_bp']}/{record['diastolic_bp']}",
                "heart_rate": record["heart_rate"],
                "blood_oxygen": record["blood_oxygen"],
                "blood_sugar": record["blood_sugar"],
                "body_temp": record["body_temp"]
            },
            assessment_time=record["timestamp"],
            hours_since_assessment=round(hours_since, 1)
        )
        alerts.append(alert)
    
    logger.info(
        f"Emergency feed requested by doctor: {current_user['_id']} "
        f"({len(alerts)} critical patients)"
    )
    
    return alerts


@router.get("/patients/priority", response_model=List[PriorityPatient])
async def get_priority_patients(
    current_user: dict = Depends(get_current_doctor),
    database: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get priority-sorted patient list.
    
    Priority Score = (Risk Level × 0.7) + (Hours Since Last Checkup × 0.3)
    
    Returns:
        List of patients sorted by priority score (highest first)
    """
    triage_repo = TriageRepository(database)
    
    # Get priority patients
    patients = await triage_repo.get_priority_patients()
    
    priority_list = []
    for record in patients:
        # Calculate hours since last checkup
        hours_since = (datetime.utcnow() - record["timestamp"]).total_seconds() / 3600
        
        patient = PriorityPatient(
            patient_id=record["user_id"],
            patient_name=f"Patient #{record['user_id'][-6:]}",
            age=record["age"],
            gestational_weeks=record["gestational_weeks"],
            risk_level=record["risk_level"],
            priority_score=round(record["priority_score"], 2),
            last_assessment=record["timestamp"],
            hours_since_checkup=round(hours_since, 1),
            alerts=record["alerts"]
        )
        priority_list.append(patient)
    
    logger.info(
        f"Priority list requested by doctor: {current_user['_id']} "
        f"({len(priority_list)} patients)"
    )
    
    return priority_list


@router.get("/patients/{patient_id}/details")
async def get_patient_details(
    patient_id: str,
    current_user: dict = Depends(get_current_doctor),
    database: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get full patient history and details.
    
    Args:
        patient_id: Patient user ID
    
    Returns:
        Patient profile and assessment history
    """
    user_repo = UserRepository(database)
    triage_repo = TriageRepository(database)
    
    # Get patient details
    patient = await user_repo.get_user_by_id(patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found"
        )
    
    # Get patient history
    history = await triage_repo.get_user_history(patient_id, limit=50)
    
    history_entries = [
        HistoryEntry(
            assessment_id=str(record["_id"]),
            timestamp=record["timestamp"],
            risk_level=record["risk_level"],
            confidence=record["confidence"],
            alerts=record["alerts"],
            vitals={
                "bp": f"{record['systolic_bp']}/{record['diastolic_bp']}",
                "heart_rate": record["heart_rate"],
                "blood_oxygen": record["blood_oxygen"],
                "blood_sugar": record["blood_sugar"],
                "body_temp": record["body_temp"]
            }
        )
        for record in history
    ]
    
    logger.info(
        f"Patient details accessed by doctor: {current_user['_id']} "
        f"(patient: {patient_id})"
    )
    
    return {
        "patient": {
            "patient_id": patient["_id"],
            "full_name": f"Patient #{patient['_id'][-6:]}",
            "age": patient.get("age"),
            "gestational_weeks": patient.get("gestational_weeks"),
            "pre_existing_conditions": patient.get("pre_existing_conditions", [])
        },
        "history": history_entries
    }
