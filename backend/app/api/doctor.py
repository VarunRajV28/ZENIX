"""
Doctor API Endpoints
====================
Endpoints for doctor dashboard and patient management.

Endpoints:
- GET /dashboard/emergency: Critical patients in last 24 hours
- GET /patients/priority: Priority-sorted patient list
- GET /patients/{patient_id}/details: Patient history and details
- GET /hitl-queue: Pending HITL cases for review
- POST /hitl-resolve: Resolve HITL case
"""

from datetime import datetime, timedelta
from typing import List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status, Body
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.models.responses import EmergencyAlert, PriorityPatient, DashboardData, HistoryEntry
from app.db.repositories import TriageRepository, UserRepository
from app.db.fsm_repository import FSMTriageRepository
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
            patient_name=record.get("patient_name") or f"Patient #{record['user_id'][-6:]}",
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
            patient_name=record.get("patient_name") or f"Patient #{record['user_id'][-6:]}",
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
                "age": record["age"],
                "bp": f"{record['systolic_bp']}/{record['diastolic_bp']}",
                "systolic_bp": record["systolic_bp"],
                "diastolic_bp": record["diastolic_bp"],
                "heart_rate": record["heart_rate"],
                "blood_oxygen": record["blood_oxygen"],
                "blood_sugar": record["blood_sugar"],
                "body_temp": record["body_temp"],
                "gestational_weeks": record["gestational_weeks"],
                "patient_name": record.get("patient_name", "Unknown")
            }
        )
        for record in history
    ]
    
    # Get latest assessment for patient info
    latest_assessment = history[0] if history else {}
    patient_name = latest_assessment.get("patient_name") or f"Patient #{patient['_id'][-6:]}"
    
    logger.info(
        f"Patient details accessed by doctor: {current_user['_id']} "
        f"(patient: {patient_id})"
    )
    
    return {
        "patient": {
            "patient_id": patient["_id"],
            "full_name": patient_name,
            "age": latest_assessment.get("age") or patient.get("age"),
            "gestational_weeks": latest_assessment.get("gestational_weeks") or patient.get("gestational_weeks"),
            "pre_existing_conditions": patient.get("pre_existing_conditions", [])
        },
        "history": history_entries
    }


# ============================================================================
# HITL (Human-in-the-Loop) Endpoints
# ============================================================================

class HITLResolveRequest(BaseModel):
    """Request to resolve HITL case."""
    case_id: str
    decision: str  # CONFIRMED, ESCALATED, DOWNGRADED
    notes: Optional[str] = None
    expected_version: int = 1


@router.get("/hitl-queue")
async def get_hitl_queue(
    limit: int = 50,
    current_user: dict = Depends(get_current_doctor),
    database: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get pending HITL cases requiring doctor review.
    
    Returns cases with low ML confidence that need human assessment.
    
    Args:
        limit: Maximum number of cases (default 50)
    
    Returns:
        List of pending HITL cases with FSM trace
    """
    fsm_repo = FSMTriageRepository(database)
    
    cases = await fsm_repo.get_hitl_queue(limit=limit)
    
    logger.info(
        f"HITL queue accessed by doctor: {current_user['_id']} "
        f"({len(cases)} pending cases)"
    )
    
    return cases


@router.post("/hitl-resolve")
async def resolve_hitl_case(
    request: HITLResolveRequest,
    current_user: dict = Depends(get_current_doctor),
    database: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Resolve a HITL case with doctor's decision.
    
    Uses optimistic locking (version_id) to prevent race conditions
    when multiple doctors access the same case.
    
    Args:
        request: Resolution details (case_id, decision, notes)
    
    Returns:
        Success status or version conflict error
    """
    fsm_repo = FSMTriageRepository(database)
    
    # Validate decision
    valid_decisions = ["CONFIRMED", "ESCALATED", "DOWNGRADED", "RESOLVED"]
    if request.decision not in valid_decisions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid decision. Must be one of: {valid_decisions}"
        )
    
    # Attempt to resolve with optimistic locking
    success = await fsm_repo.resolve_hitl_case(
        case_id=request.case_id,
        doctor_id=current_user["_id"],
        decision=request.decision,
        notes=request.notes,
        expected_version=request.expected_version
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Version conflict - case was updated by another doctor. Please refresh."
        )
    
    logger.info(
        f"HITL case resolved: {request.case_id} by {current_user['_id']} "
        f"(decision: {request.decision})"
    )
    
    return {
        "success": True,
        "message": f"Case {request.case_id} resolved as {request.decision}",
        "resolved_by": current_user["_id"],
        "decision": request.decision
    }
