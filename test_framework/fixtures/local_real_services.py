"""
Local Real Services Fixture - Non-Docker Implementation
Provides real PostgreSQL and Redis connections for Golden Path tests
"""

import asyncio
import logging
from typing import Dict, Any, AsyncGenerator
import pytest
from contextlib import asynccontextmanager
import os

logger = logging.getLogger(__name__)

try:
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.exc import OperationalError
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    create_async_engine = None
    AsyncSession = None
    OperationalError = Exception
    sessionmaker = None
    SQLALCHEMY_AVAILABLE = False

try:
    import aioredis
    REDIS_AVAILABLE = True
except ImportError:
    aioredis = None
    REDIS_AVAILABLE = False

from shared.isolated_environment import get_env


@pytest.fixture(scope="function")  
async def local_postgres_connection():
    """Local PostgreSQL connection for integration testing.
    
    Connects to a locally running PostgreSQL instance instead of Docker.
    Expects PostgreSQL to be running on localhost:5432.
    """
    env = get_env()
    
    # Load test environment
    test_env_path = "/Users/anthony/Desktop/netra-apex/.env.test.local"
    if os.path.exists(test_env_path):
        with open(test_env_path) as f:
            for line in f:
                if '=' in line and not line.strip().startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value
    
    # Check if real services should be enabled
    use_real_services = env.get("USE_REAL_SERVICES", "false").lower() == "true"
    if not use_real_services:
        logger.info("Skipping local PostgreSQL - USE_REAL_SERVICES not set to true")
        yield {
            "engine": None,
            "database_url": None, 
            "available": False
        }
        return
    
    if not SQLALCHEMY_AVAILABLE:
        logger.error("SQLAlchemy not available - cannot connect to PostgreSQL")
        yield {
            "engine": None,
            "database_url": None,
            "available": False
        }
        return
    
    # Use local PostgreSQL configuration
    database_url = env.get("DATABASE_URL", "postgresql://netra_user:netra_password@localhost:5432/netra_test")
    
    try:
        logger.info(f"Connecting to local PostgreSQL: {database_url}")
        
        # Create database engine
        engine = create_async_engine(
            database_url,
            echo=env.get("DATABASE_ECHO", "false").lower() == "true",
            pool_pre_ping=True,
            pool_recycle=300,
            pool_size=5,
            max_overflow=10
        )
        
        # Test connection
        max_retries = 10
        for attempt in range(max_retries):
            try:
                async with engine.begin() as conn:
                    await conn.execute("SELECT 1")
                logger.info("✅ Local PostgreSQL connection established")
                break
            except OperationalError as e:
                if attempt == max_retries - 1:
                    raise RuntimeError(f"Local PostgreSQL not ready after {max_retries} attempts: {e}")
                logger.info(f"PostgreSQL not ready (attempt {attempt + 1}/{max_retries}), retrying...")
                await asyncio.sleep(1)
        
        yield {
            "engine": engine,
            "database_url": database_url,
            "available": True
        }
        
        # Cleanup
        await engine.dispose()
        
    except Exception as e:
        logger.error(f"Failed to connect to local PostgreSQL: {e}")
        logger.error("Make sure PostgreSQL is running: brew services start postgresql@15")
        yield {
            "engine": None,
            "database_url": None,
            "available": False
        }


@pytest.fixture(scope="function")
async def local_redis_connection():
    """Local Redis connection for integration testing.
    
    Connects to a locally running Redis instance instead of Docker.
    Expects Redis to be running on localhost:6379.
    """
    env = get_env()
    
    # Load test environment 
    test_env_path = "/Users/anthony/Desktop/netra-apex/.env.test.local"
    if os.path.exists(test_env_path):
        with open(test_env_path) as f:
            for line in f:
                if '=' in line and not line.strip().startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value
    
    use_real_services = env.get("USE_REAL_SERVICES", "false").lower() == "true"
    if not use_real_services:
        logger.info("Skipping local Redis - USE_REAL_SERVICES not set to true")
        yield {
            "client": None,
            "redis_url": None,
            "available": False
        }
        return
        
    if not REDIS_AVAILABLE:
        logger.error("aioredis not available - cannot connect to Redis")
        yield {
            "client": None,
            "redis_url": None,
            "available": False
        }
        return
    
    redis_url = env.get("REDIS_URL", "redis://localhost:6379/1")
    
    try:
        logger.info(f"Connecting to local Redis: {redis_url}")
        
        redis_client = aioredis.from_url(redis_url, decode_responses=True)
        
        # Test connection
        await redis_client.ping()
        logger.info("✅ Local Redis connection established")
        
        yield {
            "client": redis_client,
            "redis_url": redis_url,
            "available": True
        }
        
        # Cleanup
        await redis_client.close()
        
    except Exception as e:
        logger.error(f"Failed to connect to local Redis: {e}")
        logger.error("Make sure Redis is running: brew services start redis")
        yield {
            "client": None,
            "redis_url": None,
            "available": False
        }


@pytest.fixture(scope="function")
async def local_database_session(local_postgres_connection):
    """Create a database session from local PostgreSQL connection."""
    postgres_info = local_postgres_connection
    
    if not postgres_info["available"] or not postgres_info["engine"]:
        logger.warning("PostgreSQL not available - using mock session")
        from unittest.mock import AsyncMock
        yield AsyncMock()
        return
    
    try:
        # Create session factory
        async_session_factory = sessionmaker(
            postgres_info["engine"],
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        async with async_session_factory() as session:
            yield session
            
    except Exception as e:
        logger.error(f"Failed to create database session: {e}")
        from unittest.mock import AsyncMock
        yield AsyncMock()


@pytest.fixture(scope="function")
async def local_real_services_fixture(local_postgres_connection, local_database_session, local_redis_connection):
    """Local real services fixture - provides actual service connections without Docker.
    
    This fixture provides connections to locally running services:
    - Local PostgreSQL database with active session
    - Local Redis instance
    - Environment configuration
    
    Returns the same interface as the Docker-based real_services_fixture
    but connects to local services instead.
    """
    postgres_info = local_postgres_connection
    db_session = local_database_session
    redis_info = local_redis_connection
    env = get_env()
    
    # Check overall availability
    database_available = postgres_info["available"]
    redis_available = redis_info["available"]
    services_available = database_available and redis_available
    
    logger.info(f"Local services status - PostgreSQL: {database_available}, Redis: {redis_available}")
    
    # Service endpoints (for local testing, these would be localhost)
    service_config = {
        "backend_url": "http://localhost:8000",
        "auth_url": "http://localhost:8001", 
        "frontend_url": "http://localhost:3000",
        "websocket_url": "ws://localhost:8000/ws"
    }
    
    services_info = {
        # Database info
        "db": db_session,
        "database_engine": postgres_info.get("engine"),
        "database_url": postgres_info.get("database_url"),
        "database_available": database_available,
        
        # Redis info
        "redis": redis_info.get("client"),
        "redis_url": redis_info.get("redis_url"), 
        "redis_available": redis_available,
        
        # Service endpoints
        **service_config,
        
        # Environment info
        "environment": env.get("ENVIRONMENT", "test"),
        "services_available": services_available,
        "available": services_available
    }
    
    logger.info(f"Local real services fixture ready: {services_available}")
    yield services_info
    
    logger.info("Local real services fixture cleanup complete")


# Alias for compatibility with existing tests
real_services_fixture = local_real_services_fixture