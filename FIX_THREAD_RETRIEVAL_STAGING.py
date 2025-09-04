#!/usr/bin/env python
"""Emergency fix for thread retrieval 500 error in staging.

This script implements the fix identified in the Five Whys analysis
for the GET /api/threads endpoint failure.
"""

import asyncio
from pathlib import Path

def fix_database_session_dependency():
    """Fix the database session dependency issue in staging."""
    
    # Fix 1: Update dependencies.py to handle missing context gracefully
    dependencies_file = Path("netra_backend/app/dependencies.py")
    
    fix_content = '''
# Emergency fix for staging thread retrieval issue
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager
import logging

logger = logging.getLogger(__name__)

@asynccontextmanager
async def get_request_scoped_db_session_safe() -> AsyncGenerator[AsyncSession, None]:
    """Create a request-scoped database session with proper error handling for staging.
    
    This function ensures that database sessions are properly created even
    in staging environment cold starts where the context might not be fully initialized.
    """
    from netra_backend.app.database import get_db
    
    max_retries = 3
    retry_delay = 0.1
    
    for attempt in range(max_retries):
        try:
            logger.debug(f"Creating database session (attempt {attempt + 1})")
            
            # Use the primary get_db() function with retry logic
            async with get_db() as session:
                # Validate the session is properly initialized
                if session is None:
                    raise ValueError("Database session is None")
                    
                # Test the connection with a simple query
                try:
                    await session.execute("SELECT 1")
                except Exception as e:
                    logger.warning(f"Database connection test failed: {e}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(retry_delay * (attempt + 1))
                        continue
                    raise
                
                logger.debug(f"Database session created successfully: {id(session)}")
                yield session
                return
                
        except Exception as e:
            logger.error(f"Failed to create database session (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay * (attempt + 1))
            else:
                # On final attempt, create a fallback session directly
                logger.warning("Using fallback database session creation")
                try:
                    from netra_backend.app.db.database_manager import DatabaseManager
                    async with DatabaseManager.get_async_session() as session:
                        yield session
                        return
                except Exception as fallback_error:
                    logger.critical(f"Fallback session creation also failed: {fallback_error}")
                    raise

# Update the dependency annotations to use the safe version
DbDep = Annotated[AsyncSession, Depends(get_request_scoped_db_session_safe)]
RequestScopedDbDep = Annotated[AsyncSession, Depends(get_request_scoped_db_session_safe)]
'''

    print("Fix 1: Creating safe database session dependency")
    return fix_content


def fix_startup_sequence():
    """Fix the startup sequence to ensure database is ready before accepting requests."""
    
    startup_fix = '''
# Startup sequence fix for database readiness
import asyncio
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

async def ensure_database_ready():
    """Ensure database connections are ready before accepting requests."""
    max_retries = 10
    retry_delay = 1.0
    
    logger.info("Checking database readiness...")
    
    for attempt in range(max_retries):
        try:
            # Test database connection
            async with DatabaseManager.get_async_session() as session:
                result = await session.execute("SELECT 1")
                if result:
                    logger.info("Database is ready")
                    return True
        except Exception as e:
            logger.warning(f"Database not ready (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
    
    logger.error("Database failed to become ready")
    return False

# Add to startup event handlers
async def startup_event():
    """Application startup event handler."""
    # Ensure database is ready
    if not await ensure_database_ready():
        raise RuntimeError("Database is not ready - refusing to start")
    
    logger.info("Application startup complete")
'''

    print("Fix 2: Creating database readiness check")
    return startup_fix


def fix_health_endpoint():
    """Add database connectivity check to health endpoint."""
    
    health_fix = '''
# Health endpoint with database check
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import asyncio

router = APIRouter()

@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint with database connectivity verification."""
    from netra_backend.app.db.database_manager import DatabaseManager
    
    health_status = {
        "status": "healthy",
        "service": "netra-backend",
        "database": "unknown"
    }
    
    try:
        # Check database connectivity
        async with DatabaseManager.get_async_session() as session:
            await session.execute("SELECT 1")
            health_status["database"] = "connected"
    except Exception as e:
        health_status["database"] = f"error: {str(e)}"
        health_status["status"] = "degraded"
        # Don't fail the health check completely, just indicate degraded
        
    return health_status

@router.get("/readiness")
async def readiness_check() -> Dict[str, Any]:
    """Readiness check that requires database to be available."""
    from netra_backend.app.db.database_manager import DatabaseManager
    
    try:
        async with DatabaseManager.get_async_session() as session:
            await session.execute("SELECT 1")
            return {"ready": True, "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Not ready: {str(e)}")
'''

    print("Fix 3: Creating enhanced health checks")
    return health_fix


def generate_test_script():
    """Generate a test script to verify the fix works."""
    
    test_script = '''
import asyncio
import httpx
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

async def test_thread_retrieval():
    """Test that thread retrieval works after fix."""
    
    # Test locally first
    from netra_backend.app.routes.threads_route import list_threads
    from netra_backend.app.dependencies import get_request_scoped_db_session_safe
    
    logger.info("Testing thread retrieval locally...")
    
    try:
        # Create a test session
        async with get_request_scoped_db_session_safe() as db:
            # Mock user for testing
            class MockUser:
                id = "test-user-123"
            
            # Try to list threads
            result = await list_threads(
                db=db,
                current_user=MockUser(),
                limit=20,
                offset=0
            )
            
            logger.info(f"Thread retrieval successful: {len(result)} threads")
            return True
            
    except Exception as e:
        logger.error(f"Thread retrieval failed: {e}")
        return False

async def test_staging_endpoint():
    """Test the staging endpoint directly."""
    
    staging_url = "https://api.staging.netrasystems.ai"
    
    async with httpx.AsyncClient() as client:
        try:
            # First check health
            health_response = await client.get(f"{staging_url}/health")
            logger.info(f"Health check: {health_response.json()}")
            
            # Get auth token (you'll need to implement this)
            # token = await get_staging_token()
            
            # Test thread endpoint
            # headers = {"Authorization": f"Bearer {token}"}
            # response = await client.get(
            #     f"{staging_url}/api/threads?limit=20&offset=0",
            #     headers=headers
            # )
            
            # if response.status_code == 200:
            #     logger.info(f"Staging test successful: {len(response.json())} threads")
            # else:
            #     logger.error(f"Staging test failed: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Staging test error: {e}")

if __name__ == "__main__":
    asyncio.run(test_thread_retrieval())
'''

    print("Fix 4: Creating test script")
    return test_script


def main():
    """Apply all fixes."""
    print("=" * 60)
    print("THREAD RETRIEVAL FIX FOR STAGING")
    print("=" * 60)
    
    print("\nThis script generates the fixes needed for the thread retrieval issue.")
    print("\nFixes to apply:")
    print("1. Update dependencies.py with safe session creation")
    print("2. Add database readiness check to startup")
    print("3. Enhance health endpoints with database checks")
    print("4. Test the fixes locally and in staging")
    
    print("\n" + "=" * 60)
    print("FIX 1: Safe Database Session (add to dependencies.py)")
    print("=" * 60)
    print(fix_database_session_dependency())
    
    print("\n" + "=" * 60)
    print("FIX 2: Startup Readiness Check (add to startup_module.py)")
    print("=" * 60)
    print(fix_startup_sequence())
    
    print("\n" + "=" * 60)
    print("FIX 3: Health Endpoint Enhancement (add to health route)")
    print("=" * 60)
    print(fix_health_endpoint())
    
    print("\n" + "=" * 60)
    print("FIX 4: Test Script (save as test_thread_fix.py)")
    print("=" * 60)
    print(generate_test_script())
    
    print("\n" + "=" * 60)
    print("DEPLOYMENT STEPS:")
    print("=" * 60)
    print("1. Apply fixes to the codebase")
    print("2. Test locally with: python test_thread_fix.py")
    print("3. Deploy to staging: python scripts/deploy_to_gcp.py --project netra-staging --build-local")
    print("4. Monitor GCP logs for improvements")
    print("5. Test staging endpoint with curl or browser")


if __name__ == "__main__":
    main()