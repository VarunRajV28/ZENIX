"""
Data Access Layer - Repository Pattern for MongoDB Operations
==============================================================
Abstracts database operations with type-safe interfaces.
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.db.schemas import (
    UserDocument, TriageLogDocument, IdempotencyKeyDocument,
    UserRole, RiskLevel
)
from app.utils.logger import logger


class UserRepository:
    """
    Repository for user-related database operations.
    """
    
    def __init__(self, database: AsyncIOMotorDatabase):
        self.collection = database.users
    
    async def create_user(self, user_data: UserDocument) -> str:
        """
        Create new user.
        
        Args:
            user_data: User document
        
        Returns:
            User ID as string
        """
        result = await self.collection.insert_one(user_data.model_dump())
        logger.info(f"User created: {user_data.email}", extra={"user_id": str(result.inserted_id)})
        return str(result.inserted_id)
    
    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Find user by email.
        
        Args:
            email: User email address
        
        Returns:
            User document or None
        """
        user = await self.collection.find_one({"email": email})
        if user:
            user["_id"] = str(user["_id"])
        return user
    
    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Find user by ID.
        
        Args:
            user_id: User ID string
        
        Returns:
            User document or None
        """
        try:
            user = await self.collection.find_one({"_id": ObjectId(user_id)})
            if user:
                user["_id"] = str(user["_id"])
            return user
        except Exception:
            return None
    
    async def update_user(self, user_id: str, update_data: Dict[str, Any]) -> bool:
        """
        Update user document.
        
        Args:
            user_id: User ID string
            update_data: Fields to update
        
        Returns:
            True if successful
        """
        update_data["updated_at"] = datetime.utcnow()
        result = await self.collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": update_data}
        )
        return result.modified_count > 0


class TriageRepository:
    """
    Repository for triage log operations.
    """
    
    def __init__(self, database: AsyncIOMotorDatabase):
        self.collection = database.triage_logs
    
    async def create_triage_log(self, log_data: TriageLogDocument) -> str:
        """
        Store triage assessment log.
        
        Args:
            log_data: Triage log document
        
        Returns:
            Log ID as string
        """
        result = await self.collection.insert_one(log_data.model_dump())
        logger.info(
            f"Triage log created for user: {log_data.user_id}",
            extra={
                "log_id": str(result.inserted_id),
                "risk_level": log_data.risk_level
            }
        )
        return str(result.inserted_id)
    
    async def get_user_history(
        self,
        user_id: str,
        limit: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get user's triage history.
        
        Args:
            user_id: User ID string
            limit: Maximum number of records
        
        Returns:
            List of triage logs
        """
        cursor = self.collection.find({"user_id": user_id}).sort("timestamp", -1).limit(limit)
        logs = await cursor.to_list(length=limit)
        
        for log in logs:
            log["_id"] = str(log["_id"])
        
        return logs
    
    async def get_critical_patients(
        self,
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Get all critical patients within time window.
        
        Args:
            hours: Time window in hours
        
        Returns:
            List of critical patient records
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        cursor = self.collection.find({
            "risk_level": RiskLevel.CRITICAL,
            "timestamp": {"$gte": cutoff_time}
        }).sort("timestamp", -1)
        
        logs = await cursor.to_list(length=100)
        
        for log in logs:
            log["_id"] = str(log["_id"])
        
        return logs
    
    async def get_priority_patients(
        self,
        min_risk_level: RiskLevel = RiskLevel.MEDIUM
    ) -> List[Dict[str, Any]]:
        """
        Get patients requiring attention sorted by priority.
        
        Args:
            min_risk_level: Minimum risk level filter
        
        Returns:
            List of patient records with priority scores
        """
        # Define risk level weights
        risk_weights = {
            RiskLevel.LOW: 1,
            RiskLevel.MEDIUM: 2,
            RiskLevel.HIGH: 3,
            RiskLevel.CRITICAL: 4
        }
        
        # Get latest assessment for each user
        pipeline = [
            {"$sort": {"timestamp": -1}},
            {"$group": {
                "_id": "$user_id",
                "latest_assessment": {"$first": "$$ROOT"}
            }},
            {"$replaceRoot": {"newRoot": "$latest_assessment"}},
            {"$match": {"risk_level": {"$in": [RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]}}}
        ]
        
        cursor = self.collection.aggregate(pipeline)
        patients = await cursor.to_list(length=100)
        
        # Calculate priority scores
        for patient in patients:
            patient["_id"] = str(patient["_id"])
            
            # Priority Score = (Risk Level × 0.7) + (Hours Since Last Checkup × 0.3)
            hours_since = (datetime.utcnow() - patient["timestamp"]).total_seconds() / 3600
            risk_score = risk_weights.get(patient["risk_level"], 1) * 0.7
            time_score = min(hours_since / 24, 1) * 0.3  # Normalize to 0-1
            patient["priority_score"] = risk_score + time_score
        
        # Sort by priority score descending
        patients.sort(key=lambda x: x["priority_score"], reverse=True)
        
        return patients


class IdempotencyRepository:
    """
    Repository for idempotency key management.
    """
    
    def __init__(self, database: AsyncIOMotorDatabase):
        self.collection = database.idempotency_keys
    
    async def get_cached_response(
        self,
        idempotency_key: str
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached response for idempotency key.
        
        Args:
            idempotency_key: UUID string
        
        Returns:
            Cached response or None
        """
        doc = await self.collection.find_one({"idempotency_key": idempotency_key})
        
        if doc:
            # Check if still within TTL window
            age_seconds = (datetime.utcnow() - doc["created_at"]).total_seconds()
            from app.config import settings
            
            if age_seconds < settings.idempotency_ttl_seconds:
                logger.info(
                    f"Idempotency cache hit: {idempotency_key}",
                    extra={"age_seconds": age_seconds}
                )
                return doc["response_data"]
        
        return None
    
    async def store_response(
        self,
        key_data: IdempotencyKeyDocument
    ) -> None:
        """
        Store response for idempotency key.
        
        Args:
            key_data: Idempotency key document
        """
        try:
            await self.collection.insert_one(key_data.model_dump())
            logger.debug(f"Idempotency key stored: {key_data.idempotency_key}")
        except Exception as e:
            # Duplicate key is acceptable (race condition)
            logger.debug(f"Idempotency key already exists: {key_data.idempotency_key}")
