"""
Database Migration: Update mother role to asha
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os

async def migrate_roles():
    # Connect to MongoDB Atlas from environment
    mongo_uri = os.getenv("MONGO_URI", "mongodb://mongodb:27017")
    db_name = os.getenv("MONGO_DB_NAME", "momwatch_db")
    
    print(f"Connecting to: {db_name}")
    
    client = AsyncIOMotorClient(mongo_uri)
    db = client[db_name]
    users_collection = db["users"]
    
    # Check current state
    total_users = await users_collection.count_documents({})
    print(f"Total users in database: {total_users}")
    
    # Find users with 'mother' role
    mothers_before = await users_collection.count_documents({"role": "mother"})
    print(f"Users with 'mother' role: {mothers_before}")
    
    if mothers_before > 0:
        result = await users_collection.update_many(
            {"role": "mother"},
            {"$set": {"role": "asha"}}
        )
        print(f"✅ Updated {result.modified_count} users from 'mother' to 'asha' role")
    else:
        print("⚠️ No users with 'mother' role found")
    
    # Verify the change
    mothers_after = await users_collection.count_documents({"role": "mother"})
    ashas_count = await users_collection.count_documents({"role": "asha"})
    
    print(f"\n📊 Current status:")
    print(f"   - Mother role: {mothers_after} users")
    print(f"   - ASHA role: {ashas_count} users")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(migrate_roles())
