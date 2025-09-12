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
    """Initialize auth service database tables - idempotent operation"""
    try:
        # Initialize the database connection (idempotent)
        await auth_db.initialize()
        logger.info("Auth database connection initialized")
        
        # Create all tables (idempotent operation handled in create_tables method)
        await auth_db.create_tables()
        logger.info("Auth database tables created successfully (or already existed)")
        
        # Test the tables by checking they exist (database-agnostic)
        async with auth_db.get_session() as session:
            from sqlalchemy import text, inspect
            
            # Use database-agnostic approach to check tables
            try:
                # Try to query one of our expected tables to verify creation
                result = await session.execute(text("SELECT 1 FROM auth_users LIMIT 1"))
                logger.info("Database tables verified successfully - auth_users table exists and is queryable")
            except Exception as table_check_error:
                # If direct query fails, use SQLAlchemy inspector (works on all databases)
                inspector = inspect(auth_db.engine)
                tables = await session.run_sync(lambda sync_session: inspector.get_table_names())
                auth_tables = [table for table in tables if table.startswith('auth_')]
                logger.info(f"Created auth tables: {auth_tables}")
                if not auth_tables:
                    raise RuntimeError("No auth tables were created successfully")
        
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
        logger.info(" PASS:  Auth database initialization successful")
        return 0
    else:
        logger.error(" FAIL:  Auth database initialization failed")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))