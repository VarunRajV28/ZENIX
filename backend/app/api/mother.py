"""
Mother API Endpoints
====================
Endpoints for mother dashboard and profile management.

Endpoints:
- GET /profile: Get user profile
- PUT /profile: Update profile
- GET /history: Get assessment history
- GET /health-passport: Generate health summary
"""

from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.models.requests import ProfileUpdateRequest
from app.models.responses import PatientProfile, HistoryEntry, HealthPassport
from app.db.repositories import UserRepository, TriageRepository
from app.utils.dependencies import get_database, get_current_mother
from app.utils.logger import logger


router = APIRouter(prefix="/mother", tags=["Mother"])


@router.get("/profile", response_model=PatientProfile)
async def get_profile(
    current_user: dict = Depends(get_current_mother),
    database: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get mother's profile information.
    
    Returns:
        Patient profile data
    """
    profile = PatientProfile(
        user_id=current_user["_id"],
        full_name=current_user["full_name"],
        email=current_user["email"],
        age=current_user.get("age"),
        phone=current_user.get("phone"),
        gestational_weeks=current_user.get("gestational_weeks"),
        due_date=current_user.get("due_date"),
        pre_existing_conditions=current_user.get("pre_existing_conditions", []),
        created_at=current_user["created_at"]
    )
    
    return profile


@router.put("/profile", response_model=PatientProfile)
async def update_profile(
    request: ProfileUpdateRequest,
    current_user: dict = Depends(get_current_mother),
    database: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Update mother's profile.
    
    Args:
        request: Profile update data
    
    Returns:
        Updated profile
    """
    user_repo = UserRepository(database)
    
    # Build update dictionary (only include non-None fields)
    update_data = {}
    if request.full_name is not None:
        update_data["full_name"] = request.full_name
    if request.age is not None:
        update_data["age"] = request.age
    if request.phone is not None:
        update_data["phone"] = request.phone
    if request.gestational_weeks is not None:
        update_data["gestational_weeks"] = request.gestational_weeks
    if request.pre_existing_conditions is not None:
        update_data["pre_existing_conditions"] = request.pre_existing_conditions
    
    # Update in database
    success = await user_repo.update_user(current_user["_id"], update_data)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile"
        )
    
    # Get updated user
    updated_user = await user_repo.get_user_by_id(current_user["_id"])
    
    logger.info(f"Profile updated for user: {current_user['_id']}")
    
    return PatientProfile(
        user_id=updated_user["_id"],
        full_name=updated_user["full_name"],
        email=updated_user["email"],
        age=updated_user.get("age"),
        phone=updated_user.get("phone"),
        gestational_weeks=updated_user.get("gestational_weeks"),
        due_date=updated_user.get("due_date"),
        pre_existing_conditions=updated_user.get("pre_existing_conditions", []),
        created_at=updated_user["created_at"]
    )


@router.get("/history", response_model=List[HistoryEntry])
async def get_history(
    limit: int = 30,
    current_user: dict = Depends(get_current_mother),
    database: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get mother's assessment history.
    
    Args:
        limit: Maximum number of records (default: 30)
    
    Returns:
        List of historical assessments
    """
    triage_repo = TriageRepository(database)
    
    history = await triage_repo.get_user_history(current_user["_id"], limit=limit)
    
    entries = [
        HistoryEntry(
            assessment_id=str(record["_id"]),
            timestamp=record["timestamp"],
            risk_level=record["risk_level"],
            confidence=record["confidence"],
            alerts=record["alerts"],
            vitals={
                "age": record["age"],
                "bp": f"{record['systolic_bp']}/{record['diastolic_bp']}",
                "heart_rate": record["heart_rate"],
                "blood_oxygen": record["blood_oxygen"],
                "blood_sugar": record["blood_sugar"],
                "body_temp": record["body_temp"],
                "gestational_weeks": record["gestational_weeks"]
            }
        )
        for record in history
    ]
    
    logger.info(f"History requested by user: {current_user['_id']} ({len(entries)} records)")
    
    return entries


@router.get("/health-passport", response_model=HealthPassport)
async def get_health_passport(
    current_user: dict = Depends(get_current_mother),
    database: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Generate comprehensive health passport with trends.
    
    Returns:
        Health passport with profile, history, and trends
    """
    user_repo = UserRepository(database)
    triage_repo = TriageRepository(database)
    
    # Get profile
    profile = PatientProfile(
        user_id=current_user["_id"],
        full_name=current_user["full_name"],
        email=current_user["email"],
        age=current_user.get("age"),
        phone=current_user.get("phone"),
        gestational_weeks=current_user.get("gestational_weeks"),
        due_date=current_user.get("due_date"),
        pre_existing_conditions=current_user.get("pre_existing_conditions", []),
        created_at=current_user["created_at"]
    )
    
    # Get history
    history = await triage_repo.get_user_history(current_user["_id"], limit=30)
    
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
    
    # Calculate risk trend
    risk_counts = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
    for record in history:
        risk_counts[record["risk_level"]] += 1
    
    # Extract vitals trends
    vitals_trends = {
        "blood_pressure": [
            {"timestamp": r["timestamp"], "systolic": r["systolic_bp"], "diastolic": r["diastolic_bp"]}
            for r in history
        ],
        "heart_rate": [
            {"timestamp": r["timestamp"], "value": r["heart_rate"]}
            for r in history
        ],
        "blood_sugar": [
            {"timestamp": r["timestamp"], "value": r["blood_sugar"]}
            for r in history
        ]
    }
    
    passport = HealthPassport(
        patient_profile=profile,
        assessment_history=history_entries,
        risk_trend=risk_counts,
        vitals_trends=vitals_trends,
        generated_at=datetime.utcnow()
    )
    
    logger.info(f"Health passport generated for user: {current_user['_id']}")
    
    return passport
