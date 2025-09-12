#!/usr/bin/env python3
"""Check database schema consistency between models and actual database.

Business Value Justification (BVJ):
- Segment: Platform stability (all tiers)
- Business Goal: Ensure database schema matches model definitions
- Value Impact: Prevents runtime errors from schema mismatches
- Strategic Impact: Maintains data integrity and system reliability
"""

import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncSession
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.db.base import Base
from netra_backend.app.db.models_agent import Thread, Assistant, Message, Run
from netra_backend.app.db.models_postgres import (
    User, APIKey, Event, Thread as ThreadModel, 
    AgentModel, Message as MessageModel
)
from netra_backend.app.logging_config import central_logger as logger

async def check_schema_consistency():
    """Check database schema consistency."""
    logger.info("Starting database schema consistency check")
    
    issues = []
    
    try:
        # Create engine
        engine = DatabaseManager.create_application_engine()
        
        # Test connection
        async with engine.begin() as conn:
            # Check if threads table exists
            result = await conn.execute(text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'threads'
                ORDER BY ordinal_position
            """))
            
            columns = {row[0]: {'type': row[1], 'nullable': row[2]} for row in result}
            
            if not columns:
                issues.append("threads table does not exist in database")
            else:
                logger.info(f"Found threads table with columns: {list(columns.keys())}")
                
                # Check for deleted_at column
                if 'deleted_at' not in columns:
                    issues.append("threads table missing deleted_at column")
                    logger.warning("Missing deleted_at column in threads table")
                
            # Check other critical tables
            for table_name in ['assistants', 'messages', 'runs', 'users', 'api_keys']:
                result = await conn.execute(text(f"""
                    SELECT COUNT(*) 
                    FROM information_schema.tables 
                    WHERE table_name = '{table_name}'
                """))
                count = result.scalar()
                if count == 0:
                    issues.append(f"{table_name} table does not exist")
                    
            # Check for schema mismatches
            logger.info("Checking for schema mismatches...")
            
            # Get all model tables
            model_tables = {table.name: table for table in Base.metadata.tables.values()}
            
            for table_name, table in model_tables.items():
                result = await conn.execute(text(f"""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = '{table_name}'
                """))
                db_columns = {row[0] for row in result}
                
                if db_columns:
                    model_columns = {col.name for col in table.columns}
                    
                    # Check for missing columns
                    missing_in_db = model_columns - db_columns
                    if missing_in_db:
                        for col in missing_in_db:
                            issues.append(f"{table_name} table missing column: {col}")
                            logger.warning(f"Missing column {col} in {table_name}")
                    
                    # Check for extra columns in DB
                    extra_in_db = db_columns - model_columns
                    if extra_in_db:
                        for col in extra_in_db:
                            logger.info(f"Extra column {col} in {table_name} (may be intentional)")
        
        await engine.dispose()
        
    except Exception as e:
        logger.error(f"Error checking schema: {e}")
        issues.append(f"Schema check failed: {str(e)}")
    
    # Report findings
    logger.info("=" * 60)
    if issues:
        logger.error(f"Found {len(issues)} schema issues:")
        for issue in issues:
            logger.error(f"  - {issue}")
        logger.info("\nTo fix these issues, run:")
        logger.info("  python netra_backend/app/alembic/run_migrations.py")
        return False
    else:
        logger.info("[U+2713] Database schema is consistent with models")
        return True

async def create_missing_columns():
    """Create missing columns in database tables."""
    logger.info("Attempting to create missing columns...")
    
    try:
        engine = DatabaseManager.create_application_engine()
        
        async with engine.begin() as conn:
            # Add deleted_at column to threads table if missing
            result = await conn.execute(text("""
                SELECT COUNT(*) 
                FROM information_schema.columns 
                WHERE table_name = 'threads' 
                AND column_name = 'deleted_at'
            """))
            
            if result.scalar() == 0:
                logger.info("Adding deleted_at column to threads table...")
                await conn.execute(text("""
                    ALTER TABLE threads 
                    ADD COLUMN deleted_at TIMESTAMP WITHOUT TIME ZONE
                """))
                logger.info("[U+2713] Added deleted_at column to threads table")
            
        await engine.dispose()
        return True
        
    except Exception as e:
        logger.error(f"Failed to create missing columns: {e}")
        return False

async def main():
    """Main entry point."""
    consistent = await check_schema_consistency()
    
    if not consistent:
        logger.info("\nAttempting to fix schema issues...")
        success = await create_missing_columns()
        
        if success:
            # Re-check after fix
            logger.info("\nRe-checking schema after fixes...")
            consistent = await check_schema_consistency()
    
    sys.exit(0 if consistent else 1)

if __name__ == "__main__":
    asyncio.run(main())