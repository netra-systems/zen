#!/usr/bin/env python3
"""
Auth Service Database Initialization
Creates database tables for the auth service if they don't exist.
"""
import asyncio
import logging
import os
import sys
from pathlib import Path

# Add parent directory to path for auth_service imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set up environment
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

from auth_service.auth_core.database.connection import auth_db
from auth_service.auth_core.database.models import Base

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def init_auth_database():
    """Initialize auth service database tables"""
    try:
        # Initialize the database connection
        await auth_db.initialize()
        logger.info("Auth database connection initialized")
        
        # Create all tables
        async with auth_db.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("Auth database tables created successfully")
        
        # Test the tables by checking they exist (PostgreSQL)
        async with auth_db.get_session() as session:
            from sqlalchemy import text
            result = await session.execute(
                text("SELECT tablename FROM pg_tables WHERE tablename LIKE 'auth_%'")
            )
            tables = [row[0] for row in result.fetchall()]
            logger.info(f"Created tables: {tables}")
        
        await auth_db.close()
        logger.info("Database initialization complete")
        
        return True
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return False


async def main():
    """Main initialization function"""
    logger.info("Initializing auth service database...")
    
    success = await init_auth_database()
    
    if success:
        logger.info("✅ Auth database initialization successful")
        return 0
    else:
        logger.error("❌ Auth database initialization failed")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))