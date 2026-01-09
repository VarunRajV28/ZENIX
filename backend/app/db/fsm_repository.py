"""
FSM Repository Layer - MongoDB Operations for FSM-based Triage
==============================================================
Handles persistence, idempotency, HITL queue, and FSM statistics.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.db.schemas import TriageDecisionDocument, ReviewStatus, HoneypotAlertDocument
from app.utils.logger import logger


class FSMTriageRepository:
    """
    Repository for FSM-based triage decisions with idempotency and HITL support.
    """
    
    def __init__(self, database: AsyncIOMotorDatabase):
        self.collection = database.triage_decisions
        self.honeypot_collection = database.honeypot_alerts
        self.triage_logs = database.triage_logs  # Legacy collection for backward compat
    
    async def check_idempotency(
        self,
        client_sync_uuid: str,
        ttl_minutes: int = 10
    ) -> Optional[Dict[str, Any]]:
        """
        Check if request with this UUID was already processed.
        
        Args:
            client_sync_uuid: Unique request identifier
            ttl_minutes: Time window for idempotency (default 10 minutes)
        
        Returns:
            Cached decision if found within TTL, else None
        """
        cutoff_time = datetime.utcnow() - timedelta(minutes=ttl_minutes)
        
        cached = await self.collection.find_one({
            "client_sync_uuid": client_sync_uuid,
            "created_at": {"$gte": cutoff_time}
        })
        
        if cached:
            logger.info(f"Idempotency hit: {client_sync_uuid}")
            cached["_id"] = str(cached["_id"])
            return cached
        
        return None
    
    async def save_triage_decision(
        self,
        decision_data: Dict[str, Any]
    ) -> str:
        """
        Save FSM triage decision to database.
        
        Performs dual write to:
        1. triage_decisions (new FSM collection)
        2. triage_logs (legacy collection for backward compatibility)
        
        Args:
            decision_data: Complete FSM execution result
        
        Returns:
            Inserted document ID
        """
        # Insert to new FSM collection
        result = await self.collection.insert_one(decision_data)
        decision_id = str(result.inserted_id)
        
        # Dual write to legacy triage_logs for backward compatibility
        if decision_data.get("fsm_state") == "DONE":
            legacy_log = {
                "user_id": decision_data["user_id"],
                "patient_name": decision_data.get("patient_name"),
                "age": decision_data["input_vitals"].get("age"),
                "systolic_bp": decision_data["input_vitals"].get("systolic_bp"),
                "diastolic_bp": decision_data["input_vitals"].get("diastolic_bp"),
                "blood_sugar": decision_data["input_vitals"].get("blood_sugar"),
                "body_temp": decision_data["input_vitals"].get("body_temp"),
                "heart_rate": decision_data["input_vitals"].get("heart_rate"),
                "blood_oxygen": decision_data["input_vitals"].get("blood_oxygen"),
                "gestational_weeks": decision_data["input_vitals"].get("gestational_weeks"),
                "risk_level": decision_data.get("final_risk_level"),
                "confidence": decision_data.get("confidence", 0.0),
                "alerts": decision_data.get("alerts", []),
                "clinical_notes": decision_data.get("clinical_notes", []),
                "engine_source": decision_data.get("engine_source", "FSM"),
                "processing_time_ms": int(decision_data.get("processing_time_ms", 0)),
                "timestamp": decision_data.get("created_at", datetime.utcnow())
            }
            await self.triage_logs.insert_one(legacy_log)
        
        logger.info(f"Triage decision saved: {decision_id}")
        return decision_id
    
    async def get_hitl_queue(
        self,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get pending HITL cases for doctor review.
        
        Args:
            limit: Maximum number of cases to return
        
        Returns:
            List of pending HITL cases sorted by creation time
        """
        cursor = self.collection.find({
            "requires_hitl": True,
            "review_status": ReviewStatus.PENDING
        }).sort("created_at", -1).limit(limit)
        
        cases = await cursor.to_list(length=limit)
        
        # Convert ObjectId to string and add decision_id field for frontend
        for case in cases:
            case["decision_id"] = str(case["_id"])
            case["_id"] = str(case["_id"])
            
            # Ensure ML fields exist with defaults
            if "final_risk_level" not in case or case["final_risk_level"] is None:
                case["ml_risk_level"] = "UNKNOWN"
            else:
                case["ml_risk_level"] = case["final_risk_level"]
            
            if "confidence" not in case or case["confidence"] is None:
                case["ml_confidence"] = 0.0
            else:
                case["ml_confidence"] = case["confidence"]
            
            # Add priority score if not present
            if "ml_priority_score" not in case:
                case["ml_priority_score"] = 0.0
            
            # Add vitals field from input_vitals
            if "input_vitals" in case:
                case["vitals"] = case["input_vitals"]
        
        logger.info(f"HITL queue retrieved: {len(cases)} pending cases")
        return cases
    
    async def resolve_hitl_case(
        self,
        case_id: str,
        doctor_id: str,
        final_risk_level: str,
        notes: Optional[str] = None,
        expected_version: int = 1
    ) -> bool:
        """
        Resolve a HITL case with optimistic locking.
        
        Args:
            case_id: Triage decision ID
            doctor_id: Doctor user ID
            final_risk_level: Final risk assessment (LOW, MEDIUM, HIGH, CRITICAL)
            notes: Optional review notes
            expected_version: Expected version for optimistic locking
        
        Returns:
            True if update succeeded, False if version conflict
        """
        from bson import ObjectId
        
        update_data = {
            "review_status": ReviewStatus.RESOLVED,
            "final_risk_level": final_risk_level,
            "reviewed_by": doctor_id,
            "reviewed_at": datetime.utcnow(),
            "review_notes": notes,
            "updated_at": datetime.utcnow(),
            "version_id": expected_version + 1
        }
        
        result = await self.collection.update_one(
            {
                "_id": ObjectId(case_id),
                "version_id": expected_version  # Optimistic lock
            },
            {"$set": update_data}
        )
        
        if result.modified_count > 0:
            logger.info(f"HITL case resolved: {case_id} by {doctor_id} -> {final_risk_level}")
            return True
        else:
            logger.warning(f"HITL resolution failed (version conflict): {case_id}")
            return False
    
    async def get_patient_history(
        self,
        patient_uuid: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get FSM decision history for a specific patient.
        
        Args:
            patient_uuid: Unique patient identifier
            limit: Maximum number of records
        
        Returns:
            List of triage decisions sorted by most recent
        """
        cursor = self.collection.find({
            "patient_uuid": patient_uuid
        }).sort("created_at", -1).limit(limit)
        
        history = await cursor.to_list(length=limit)
        
        for record in history:
            record["_id"] = str(record["_id"])
        
        return history
    
    async def get_fsm_statistics(self) -> Dict[str, Any]:
        """
        Get FSM execution statistics for monitoring dashboard.
        
        Returns:
            Statistics dict with counts, averages, and distributions
        """
        # Query triage decisions collection for FSM statistics
        pipeline = [
            {
                "$facet": {
                    "total_decisions": [{"$count": "count"}],
                    "state_distribution": [
                        {"$group": {"_id": "$fsm_state", "count": {"$sum": 1}}}
                    ],
                    "hitl_cases": [
                        {"$match": {"requires_hitl": True}},
                        {"$group": {
                            "_id": "$review_status",
                            "count": {"$sum": 1}
                        }}
                    ],
                    "avg_processing_time": [
                        {"$group": {
                            "_id": None,
                            "avg_ms": {"$avg": "$processing_time_ms"}
                        }}
                    ]
                }
            }
        ]
        
        cursor = self.collection.aggregate(pipeline)
        results = await cursor.to_list(length=1)
        
        # Get honeypot trigger count from the correct collection (honeypot_alerts)
        honeypot_count = await self.honeypot_collection.count_documents({})
        
        if not results:
            return {
                "total_decisions": 0,
                "state_distribution": {},
                "honeypot_triggers": honeypot_count,
                "hitl_pending": 0,
                "avg_processing_time_ms": 0
            }
        
        stats = results[0]
        
        return {
            "total_decisions": stats["total_decisions"][0]["count"] if stats["total_decisions"] else 0,
            "state_distribution": {
                item["_id"]: item["count"] 
                for item in stats.get("state_distribution", [])
            },
            "honeypot_triggers": honeypot_count,
            "hitl_cases": {
                item["_id"]: item["count"]
                for item in stats.get("hitl_cases", [])
            },
            "avg_processing_time_ms": round(
                stats["avg_processing_time"][0]["avg_ms"], 2
            ) if stats.get("avg_processing_time") else 0
        }
    
    async def log_honeypot_alert(
        self,
        triggered_field: str,
        endpoint: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_payload: Dict[str, Any] = None
    ) -> None:
        """
        Log honeypot trigger to dedicated collection for security monitoring.
        
        Args:
            triggered_field: Field name that triggered honeypot
            endpoint: API endpoint that was targeted
            ip_address: Client IP address
            user_agent: Client user agent string
            request_payload: Sanitized request payload
        """
        alert = {
            "triggered_field": triggered_field,
            "endpoint": endpoint,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "request_payload": request_payload or {},
            "timestamp": datetime.utcnow()
        }
        
        await self.honeypot_collection.insert_one(alert)
        logger.warning(f"Honeypot alert logged: {triggered_field} at {endpoint}")
    
    async def create_indexes(self) -> None:
        """
        Create MongoDB indexes for optimal query performance.
        
        Should be called during application startup.
        """
        # Unique index on client_sync_uuid for idempotency
        await self.collection.create_index("client_sync_uuid", unique=True)
        
        # Compound index for patient history queries
        await self.collection.create_index([("patient_uuid", 1), ("created_at", -1)])
        
        # Index for HITL queue queries
        await self.collection.create_index([("requires_hitl", 1), ("review_status", 1)])
        
        # Index for honeypot monitoring
        await self.collection.create_index("is_honeypot_triggered")
        
        # TTL index for honeypot alerts (optional - auto-delete after 90 days)
        await self.honeypot_collection.create_index(
            "timestamp",
            expireAfterSeconds=7776000  # 90 days
        )
        
        logger.info("FSM repository indexes created")
