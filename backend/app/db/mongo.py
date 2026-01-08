"""
MongoDB Client - Async Connection Management with Retry Logic
==============================================================
Implements connection pooling, retry logic with exponential backoff,
and graceful shutdown for MongoDB using Motor async driver.

Defensive Engineering:
- 3 connection attempts with exponential backoff (1s, 2s, 4s)
- Validates connection on startup with ping command
- Logs all connection events
- Raises fatal exception if unreachable after retries
"""

import asyncio
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from app.config import settings
from app.utils.logger import logger


class MongoDBClient:
    """
    MongoDB client with connection pooling and retry logic.
    """
    
    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.database: Optional[AsyncIOMotorDatabase] = None
        self._is_connected: bool = False
    
    async def connect(self) -> None:
        """
        Establish connection to MongoDB with retry logic.
        
        Raises:
            RuntimeError: If connection fails after 3 attempts
        """
        max_attempts = 3
        
        for attempt in range(1, max_attempts + 1):
            try:
                logger.info(
                    f"MongoDB connection attempt {attempt}/{max_attempts}",
                    extra={"uri": settings.MONGO_URI, "database": settings.MONGO_DB_NAME}
                )
                
                # Create client with connection pooling
                self.client = AsyncIOMotorClient(
                    settings.MONGO_URI,
                    maxPoolSize=settings.MONGO_MAX_POOL_SIZE,
                    minPoolSize=settings.MONGO_MIN_POOL_SIZE,
                    serverSelectionTimeoutMS=5000,  # 5 second timeout
                    connectTimeoutMS=10000  # 10 second timeout
                )
                
                # Validate connection with ping
                await self.client.admin.command('ping')
                
                # Get database reference
                self.database = self.client[settings.MONGO_DB_NAME]
                self._is_connected = True
                
                logger.info(
                    "✓ MongoDB connection established successfully",
                    extra={
                        "database": settings.MONGO_DB_NAME,
                        "attempt": attempt
                    }
                )
                
                # Create indexes
                await self._create_indexes()
                
                return
            
            except (ConnectionFailure, ServerSelectionTimeoutError) as e:
                logger.error(
                    f"MongoDB connection attempt {attempt} failed: {str(e)}",
                    extra={"error_type": type(e).__name__, "attempt": attempt}
                )
                
                if attempt < max_attempts:
                    # Exponential backoff: 2^attempt seconds
                    sleep_time = 2 ** attempt
                    logger.info(f"Retrying in {sleep_time} seconds...")
                    await asyncio.sleep(sleep_time)
                else:
                    # All attempts exhausted
                    error_msg = (
                        f"FATAL: MongoDB unreachable after {max_attempts} attempts. "
                        f"URI: {settings.MONGO_URI}. "
                        "Please verify MongoDB is running and accessible."
                    )
                    logger.critical(error_msg)
                    raise RuntimeError(error_msg) from e
    
    async def _create_indexes(self) -> None:
        """
        Create database indexes for optimal query performance.
        """
        try:
            # Users collection indexes
            await self.database.users.create_index("email", unique=True)
            await self.database.users.create_index("role")
            
            # Triage logs indexes
            await self.database.triage_logs.create_index("user_id")
            await self.database.triage_logs.create_index("timestamp")
            await self.database.triage_logs.create_index("risk_level")
            await self.database.triage_logs.create_index([("user_id", 1), ("timestamp", -1)])
            
            # Idempotency keys indexes
            await self.database.idempotency_keys.create_index("idempotency_key", unique=True)
            await self.database.idempotency_keys.create_index(
                "created_at",
                expireAfterSeconds=settings.idempotency_ttl_seconds
            )
            
            logger.info("✓ Database indexes created successfully")
        
        except Exception as e:
            logger.warning(f"Index creation warning: {str(e)}")
    
    async def close(self) -> None:
        """
        Gracefully close MongoDB connection.
        """
        if self.client:
            self.client.close()
            self._is_connected = False
            logger.info("MongoDB connection closed")
    
    def get_database(self) -> AsyncIOMotorDatabase:
        """
        Get database instance.
        
        Returns:
            AsyncIOMotorDatabase instance
        
        Raises:
            RuntimeError: If database is not connected
        """
        if not self._is_connected or self.database is None:
            raise RuntimeError(
                "Database not connected. Call connect() first."
            )
        return self.database
    
    @property
    def is_connected(self) -> bool:
        """Check if database is connected."""
        return self._is_connected


# Global database client instance
db_client = MongoDBClient()
