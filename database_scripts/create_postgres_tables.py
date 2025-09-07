#!/usr/bin/env python3
"""
PostgreSQL Table Creation Script for Netra Dev Database

This script creates all PostgreSQL tables in the netra_dev database by:
1. Importing Base from netra_backend.app.db.base
2. Explicitly importing ALL model classes to register them with Base.metadata
3. Creating an async engine and using Base.metadata.create_all()
4. Verifying tables were created successfully

Database URL: postgresql+asyncpg://postgres:DTprdt5KoQXlEG4Gh9lF@localhost:5433/netra_dev
"""

import asyncio
import sys

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Import Base first
from netra_backend.app.db.base import Base

# Agent models
from netra_backend.app.db.models_agent import (
    ApexOptimizerAgentRun,
    ApexOptimizerAgentRunReport,
    Assistant,
    Message,
    Run,
    Step,
    Thread,
)

# Agent State models
from netra_backend.app.db.models_agent_state import (
    AgentRecoveryLog,
    AgentStateSnapshot,
    AgentStateTransaction,
)

# Content models
from netra_backend.app.db.models_content import (
    Analysis,
    AnalysisResult,
    Corpus,
    CorpusAuditLog,
    Reference,
)

# MCP Client models
from netra_backend.app.db.models_mcp_client import (
    MCPExternalServer,
    MCPResourceAccess,
    MCPToolExecution,
)

# Supply models  
from netra_backend.app.db.models_supply import (
    AISupplyItem,
    AvailabilityStatus,
    ResearchSession,
    ResearchSessionStatus,
    Supply,
    SupplyOption,
    SupplyUpdateLog,
)

# Explicitly import ALL model classes to ensure they're registered with Base.metadata
# User models
from netra_backend.app.db.models_user import Secret, ToolUsageLog, User

# TODO this should be from env
# Database configuration
DATABASE_URL = "postgresql+asyncpg://postgres:DTprdt5KoQXlEG4Gh9lF@localhost:5433/netra_dev"


async def create_all_tables():
    """
    Create all PostgreSQL tables using SQLAlchemy metadata.
    """
    print("Starting PostgreSQL table creation process...")
    print(f"Database URL: {DATABASE_URL}")
    
    try:
        # Create async engine
        engine = create_async_engine(
            DATABASE_URL,
            echo=True,  # Show SQL statements
            future=True
        )
        
        print("\nSuccessfully created database engine")
        
        # Test connection
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT version()"))
            pg_version = result.scalar()
            print(f"Connected to PostgreSQL: {pg_version}")
        
        # Display all registered models
        print(f"\nFound {len(Base.metadata.tables)} registered tables:")
        for table_name in sorted(Base.metadata.tables.keys()):
            print(f"   - {table_name}")
        
        # Create all tables
        print("\nCreating tables...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        print("All tables created successfully!")
        
        # Verify tables were created
        print("\nVerifying created tables...")
        async with engine.begin() as conn:
            result = await conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name
            """))
            
            created_tables = [row[0] for row in result.fetchall()]
            
        print(f"\nSuccessfully created {len(created_tables)} tables in database:")
        for table_name in created_tables:
            print(f"   + {table_name}")
        
        # Check for any missing tables
        expected_tables = set(Base.metadata.tables.keys())
        actual_tables = set(created_tables)
        
        missing_tables = expected_tables - actual_tables
        if missing_tables:
            print(f"\nWARNING: Missing tables: {missing_tables}")
        else:
            print(f"\nSUCCESS: All {len(expected_tables)} expected tables were created!")
        
        # Show table details
        print("\nTable creation summary:")
        print(f"   - Expected tables: {len(expected_tables)}")
        print(f"   - Created tables: {len(actual_tables)}")
        print(f"   - Missing tables: {len(missing_tables)}")
        
        await engine.dispose()
        print("\nDatabase connection closed successfully")
        
        return True
        
    except Exception as e:
        print(f"\nError creating tables: {e}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main execution function."""
    print("=" * 70)
    print("NETRA POSTGRESQL TABLE CREATION SCRIPT")
    print("=" * 70)
    
    success = await create_all_tables()
    
    if success:
        print("\n" + "=" * 70)
        print("TABLE CREATION COMPLETED SUCCESSFULLY!")
        print("=" * 70)
        sys.exit(0)
    else:
        print("\n" + "=" * 70)
        print("TABLE CREATION FAILED!")
        print("=" * 70)
        sys.exit(1)


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())