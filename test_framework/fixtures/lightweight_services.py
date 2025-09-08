"""Lightweight Service Fixtures - Integration Testing Without Docker

This module provides integration test fixtures that work without Docker 
or external services. These fixtures create lightweight service stubs
that allow integration tests to validate business logic and API contracts
without requiring a full infrastructure stack.

Business Value:
- Segment: Platform/Internal - Test Infrastructure  
- Business Goal: Enable integration testing without Docker dependencies
- Value Impact: Fast integration tests that work in any environment
- Strategic Impact: Enable CI/CD pipelines without Docker overhead

CRITICAL: These are LIGHTWEIGHT service implementations, not full services.
Use for testing business logic integration, not full system behavior.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, AsyncGenerator
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone
import json
import uuid

import pytest
from contextlib import asynccontextmanager

# Import environment isolation
from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)


@pytest.fixture(scope="session") 
async def lightweight_postgres_connection():
    """Lightweight PostgreSQL connection for integration testing.
    
    This fixture provides an in-memory SQLite database that mimics
    PostgreSQL behavior for integration testing without Docker.
    
    Yields:
        Dict containing database engine, URL, and environment info
    """
    try:
        from sqlalchemy import create_engine
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
        from sqlalchemy.pool import StaticPool
    except ImportError:
        logger.warning("SQLAlchemy not available - using mock database connection")
        yield {
            "engine": None,
            "database_url": "sqlite+aiosqlite:///:memory:",
            "environment": "test", 
            "available": False
        }
        return
    
    # Use in-memory SQLite for lightweight integration testing
    database_url = "sqlite+aiosqlite:///:memory:"
    
    engine = create_async_engine(
        database_url,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
        echo=False  # Set to True for SQL debugging
    )
    
    try:
        # Test the connection
        async with engine.begin() as conn:
            await conn.run_sync(lambda _: None)  # Simple connection test
        
        logger.info(f"Lightweight PostgreSQL connection established: {database_url}")
        
        yield {
            "engine": engine,
            "database_url": database_url,
            "environment": "test",
            "available": True
        }
        
    finally:
        if engine:
            await engine.dispose()
            logger.info("Lightweight PostgreSQL connection closed")


@pytest.fixture(scope="function")
async def lightweight_test_database(lightweight_postgres_connection):
    """Fixture that provides a lightweight test database session.
    
    Creates tables and provides a clean database session for each test.
    Automatically rolls back changes after test completion.
    """
    postgres_info = lightweight_postgres_connection
    
    if not postgres_info["available"]:
        logger.warning("Lightweight database not available - using mock session")
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock() 
        mock_session.close = AsyncMock()
        yield mock_session
        return
    
    engine = postgres_info["engine"]
    
    # Import models to create tables
    try:
        from netra_backend.app.models.database import Base
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.debug("Database tables created for lightweight testing")
    except ImportError:
        logger.info("Database models not available - using raw SQL")
    
    # Create session
    from sqlalchemy.ext.asyncio import AsyncSession
    async with AsyncSession(engine) as session:
        try:
            yield session
        finally:
            await session.rollback()  # Always rollback to keep tests isolated
            await session.close()


@pytest.fixture(scope="function")
async def lightweight_services_fixture(lightweight_postgres_connection, lightweight_test_database):
    """Lightweight services fixture for integration testing without Docker.
    
    This fixture provides lightweight service implementations that work
    without external dependencies. Perfect for testing business logic
    integration and API contracts.
    
    Args:
        lightweight_postgres_connection: Lightweight database connection info
        lightweight_test_database: In-memory database session

    Yields:
        Dict: Lightweight service connections and configuration
    """
    postgres_info = lightweight_postgres_connection
    db_session = lightweight_test_database
    env = get_env()
    
    # Create lightweight service stubs
    backend_url = "http://localhost:8000"  # URL only, no actual service
    auth_url = "http://localhost:8081"     # URL only, no actual service
    
    # Create service availability info (all false since no real services)
    services_available = {
        "backend": False,  # No real backend service running
        "auth": False      # No real auth service running  
    }
    
    # Create auth service stub for integration testing
    auth_service_stub = {
        "validate_token": AsyncMock(return_value={
            "valid": True,
            "user_id": str(uuid.uuid4()),
            "username": "test_user",
            "is_admin": False,
            "exp": int(datetime.now(timezone.utc).timestamp()) + 3600
        }),
        "create_session": AsyncMock(return_value={
            "session_id": str(uuid.uuid4()),
            "expires_at": datetime.now(timezone.utc).timestamp() + 3600
        }),
        "validate_session": AsyncMock(return_value={"valid": True}),
        "invalidate_session": AsyncMock(return_value={"success": True})
    }
    
    # Create Redis stub for session storage
    redis_stub = {
        "get": AsyncMock(return_value=None),
        "set": AsyncMock(return_value=True), 
        "delete": AsyncMock(return_value=True),
        "exists": AsyncMock(return_value=False)
    }
    
    logger.info("Lightweight services fixture initialized - no external dependencies required")
    
    yield {
        "backend_url": backend_url,
        "auth_url": auth_url,
        "postgres": postgres_info["engine"],
        "db": db_session,
        "database_url": postgres_info["database_url"],
        "environment": postgres_info["environment"],
        "services_available": services_available,
        "database_available": postgres_info["available"],
        "auth_service": auth_service_stub,
        "redis": redis_stub,
        "lightweight": True  # Flag to indicate this is lightweight mode
    }


@pytest.fixture(scope="function")
async def lightweight_auth_context():
    """Lightweight authentication context for integration testing.
    
    Provides pre-configured auth tokens and user context without
    requiring actual auth service connectivity.
    """
    # Create mock JWT token data
    user_id = str(uuid.uuid4())
    test_token = "test_jwt_token_" + user_id
    
    auth_context = {
        "user_id": user_id,
        "username": "integration_test_user", 
        "token": test_token,
        "is_admin": False,
        "session_id": str(uuid.uuid4()),
        "expires_at": int(datetime.now(timezone.utc).timestamp()) + 3600
    }
    
    # Mock token validation function
    async def mock_validate_token(token: str) -> Dict[str, Any]:
        if token == test_token:
            return {
                "valid": True,
                "user_id": auth_context["user_id"],
                "username": auth_context["username"],
                "is_admin": auth_context["is_admin"],
                "exp": auth_context["expires_at"]
            }
        return {"valid": False, "error": "Invalid token"}
    
    auth_context["validate_token"] = mock_validate_token
    
    logger.info(f"Lightweight auth context created for user: {user_id}")
    return auth_context


# Alias for backward compatibility  
@pytest.fixture(scope="function")
async def integration_services(lightweight_services_fixture):
    """Alias for lightweight_services_fixture for backward compatibility."""
    return lightweight_services_fixture