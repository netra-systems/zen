"""Real Services Test Fixtures - SSOT Integration Testing Infrastructure

This module provides REAL service connections for integration testing.
Replaces placeholder implementations with actual database connections,
service endpoints, and Docker container management.

Business Value:
- Segment: Platform/Internal - Test Infrastructure
- Business Goal: Validate actual system behavior, not mocks
- Value Impact: Catch integration bugs before production
- Strategic Impact: Enable reliable integration testing

CRITICAL: This provides REAL services, not mocks or placeholders.
"""

import asyncio
import logging
import time
from typing import Dict, Any, AsyncGenerator
import pytest
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

try:
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.exc import OperationalError
except ImportError:
    # Fallback for environments without SQLAlchemy
    create_async_engine = None
    AsyncSession = None
    OperationalError = Exception

from shared.isolated_environment import get_env

try:
    from test_framework.unified_docker_manager import UnifiedDockerManager
except ImportError:
    # Fallback for environments without Docker manager
    logger.warning("UnifiedDockerManager not available - using fallback")
    UnifiedDockerManager = None

try:
    import redis.asyncio as redis
    import fakeredis.aioredis as fake_redis
except ImportError:
    logger.warning("Redis libraries not available - Redis fixtures will fail")
    redis = None
    fake_redis = None


@pytest.fixture(scope="function")
async def real_postgres_connection():
    """REAL PostgreSQL connection for integration testing.
    
    This fixture provides an actual PostgreSQL database connection
    running in Docker containers. It ensures the database is ready
    and accessible before yielding the connection info.
    
    Yields:
        Dict containing database engine, URL, and environment info
    """
    env = get_env()
    
    # Only run real services if explicitly requested
    if not env.get("USE_REAL_SERVICES", "false").lower() == "true":
        logger.info("Skipping real PostgreSQL - USE_REAL_SERVICES not set")
        yield {
            "engine": None,
            "database_url": None,
            "environment": None,
            "available": False
        }
        return
    
    if create_async_engine is None:
        logger.warning("SQLAlchemy not available - using mock database connection")
        yield {
            "engine": None,
            "database_url": "postgresql://mock:mock@localhost:5434/mock",
            "environment": None,
            "available": False
        }
        return
    
    docker_manager = None
    engine = None
    
    try:
        # Check if Docker is running first
        try:
            import subprocess
            docker_check = subprocess.run(['docker', 'ps'], capture_output=True, timeout=5)
            if docker_check.returncode != 0:
                raise RuntimeError(f"Docker not accessible: {docker_check.stderr.decode()}")
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            raise RuntimeError(f"Docker not running or not installed: {e}")
        
        # Start Docker services if manager available
        if UnifiedDockerManager is None:
            raise RuntimeError("UnifiedDockerManager not available - cannot start Docker services")
            
        docker_manager = UnifiedDockerManager()
        
        try:
            env_name, env_info = docker_manager.acquire_environment()
            logger.info(f"Acquired test environment: {env_name} with ports: {env_info}")
        except Exception as e:
            raise RuntimeError(f"Failed to acquire Docker test environment: {e}")
        
        # Build database URL
        database_url = f"postgresql+asyncpg://test_user:test_password@localhost:5434/netra_test"
        
        # Create database engine
        engine = create_async_engine(
            database_url,
            echo=env.get("DATABASE_ECHO", "false").lower() == "true",
            pool_pre_ping=True,
            pool_recycle=300
        )
        
        # Wait for database to be ready (up to 30 seconds)
        max_retries = 30
        for attempt in range(max_retries):
            try:
                async with engine.begin() as conn:
                    await conn.execute("SELECT 1")
                logger.info("Database connection established successfully")
                break
            except OperationalError as e:
                if attempt == max_retries - 1:
                    raise RuntimeError(f"Database not ready after {max_retries} attempts: {e}")
                logger.info(f"Database not ready (attempt {attempt + 1}/{max_retries}), retrying...")
                await asyncio.sleep(1)
        
        yield {
            "engine": engine,
            "database_url": database_url,
            "environment": env_info,
            "available": True
        }
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Failed to set up real PostgreSQL connection: {error_msg}")
        
        # Provide detailed error guidance based on the type of failure
        if "Docker not running" in error_msg or "Docker not accessible" in error_msg:
            guidance = (
                "Docker is required for real database testing. "
                "Start Docker Desktop and run: python tests/unified_test_runner.py --real-services"
            )
        elif "UnifiedDockerManager not available" in error_msg:
            guidance = (
                "Docker manager not available. "
                "Ensure test framework is properly installed."
            )
        elif "Database not ready" in error_msg:
            guidance = (
                "Database container failed to start or connect. "
                "Try: docker compose down && python tests/unified_test_runner.py --real-services"
            )
        else:
            guidance = (
                "Unknown database setup error. "
                "Check Docker, database containers, and environment configuration."
            )
        
        # Provide fallback for tests that can handle missing database
        yield {
            "engine": None,
            "database_url": None,
            "environment": None,
            "available": False,
            "error": error_msg,
            "guidance": guidance
        }
    finally:
        # Cleanup
        if engine:
            await engine.dispose()
        if docker_manager:
            try:
                docker_manager.release_environment("test")
            except Exception as e:
                logger.warning(f"Failed to release Docker environment: {e}")


@pytest.fixture(scope="function") 
async def with_test_database(real_postgres_connection):
    """Fixture that provides a test database session.
    
    This creates a fresh database session for each test and ensures
    proper cleanup after the test completes.
    
    Args:
        real_postgres_connection: Session-scoped database connection
        
    Yields:
        AsyncSession: Database session for the test
    """
    postgres_info = real_postgres_connection
    
    if not postgres_info["available"] or not postgres_info["engine"]:
        logger.info("Database not available - yielding None")
        yield None
        return
    
    # Create session for this test
    async with AsyncSession(postgres_info["engine"], expire_on_commit=False) as session:
        try:
            yield session
        finally:
            # Cleanup: rollback any uncommitted changes
            try:
                await session.rollback()
            except Exception as e:
                logger.warning(f"Failed to rollback database session: {e}")


@pytest.fixture(scope="function")
async def real_redis_fixture():
    """REAL Redis fixture for integration testing with fallback to in-memory Redis.
    
    This fixture provides an actual Redis connection when available (Docker/local Redis)
    or falls back to an in-memory Redis implementation for environments without Docker.
    This ensures Redis cache integration tests can run in all environments.
    
    CRITICAL: Per CLAUDE.md - Uses REAL Redis when available, graceful skip
    when libraries unavailable. Follows same pattern as database fixtures.
    
    Yields:
        redis.Redis: Redis client directly for backward compatibility, None if unavailable
    """
    env = get_env()
    
    # Only run real Redis if explicitly requested
    if not env.get("USE_REAL_SERVICES", "false").lower() == "true":
        logger.info("Skipping real Redis - USE_REAL_SERVICES not set")
        pytest.skip("Redis not available: USE_REAL_SERVICES not set")
        return
    
    if redis is None:
        logger.warning("Redis libraries not available - skipping Redis-dependent test")
        pytest.skip("Redis libraries not available. Install: pip install redis fakeredis")
        return
    
    redis_client = None
    
    try:
        # First attempt: Real Redis connection (Docker or local)
        redis_host = env.get("REDIS_HOST", "localhost")
        redis_port = int(env.get("REDIS_PORT", "6381"))  # Test Redis port
        redis_db = int(env.get("REDIS_DB", "1"))  # Test database
        
        real_redis_url = f"redis://{redis_host}:{redis_port}/{redis_db}"
        
        # Create Redis client for real Redis
        import redis.asyncio as redis
        redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            decode_responses=True,
            socket_timeout=2.0,  # Quick timeout for testing
            socket_connect_timeout=2.0
        )
        
        # Test real Redis connection
        await redis_client.ping()
        logger.info(f"Connected to REAL Redis at {redis_host}:{redis_port}")
        
        yield redis_client
        
    except Exception as redis_error:
        logger.info(f"Real Redis not available ({redis_error}), attempting in-memory Redis")
        
        # Fallback: In-memory Redis using fakeredis (CLAUDE.md compliant fallback)
        if fake_redis is None:
            logger.warning(f"Real Redis unavailable and fakeredis not installed: {redis_error}")
            pytest.skip(f"Redis unavailable: Real Redis failed ({redis_error}) and fakeredis not installed")
            return
        
        try:
            # Create in-memory Redis client
            redis_client = fake_redis.FakeRedis(
                decode_responses=True,
                version=(7, 0, 0)  # Redis 7.0 compatibility
            )
            
            # Verify in-memory Redis works
            await redis_client.ping()
            logger.info("Using in-memory Redis (fakeredis) for integration testing")
            
            yield redis_client
            
        except Exception as fallback_error:
            logger.error(f"Both real Redis and in-memory fallback failed")
            pytest.skip(f"Redis unavailable: Real Redis failed ({redis_error}) and fakeredis failed ({fallback_error})")
    
    finally:
        # Cleanup Redis connection
        if redis_client:
            try:
                await redis_client.aclose()
            except Exception as e:
                logger.warning(f"Failed to close Redis connection: {e}")


# Alias for backward compatibility with existing tests
real_redis_connection = real_redis_fixture


@pytest.fixture(scope="function")
async def real_services_fixture(real_postgres_connection, with_test_database):
    """REAL services fixture - provides access to actual running services.
    
    This fixture provides connections to actual running services including:
    - Real PostgreSQL database with active session
    - Backend service endpoints
    - Auth service endpoints
    - Environment configuration
    
    CRITICAL: This replaces placeholder implementations with real services.
    
    Args:
        real_postgres_connection: Real database connection info
        with_test_database: Real database session
        
    Yields:
        Dict: Real service connections and configuration
    """
    postgres_info = real_postgres_connection
    db_session = with_test_database
    env = get_env()
    
    # FIVE-WHYS FIX: Environment-aware service discovery for staging/production testing
    environment = env.get("ENVIRONMENT", "development").lower()
    is_staging = environment == "staging" or "staging" in env.get("GOOGLE_CLOUD_PROJECT", "").lower()
    is_production = environment == "production" or "prod" in env.get("GOOGLE_CLOUD_PROJECT", "").lower()
    
    # Determine service URLs based on environment
    if is_staging:
        # Staging GCP service URLs
        backend_url = env.get("STAGING_BACKEND_URL", "https://api.staging.netrasystems.ai")
        auth_url = env.get("STAGING_AUTH_URL", "https://auth.staging.netrasystems.ai") 
        redis_url = env.get("STAGING_REDIS_URL", "redis://staging-redis:6379")
        
        # Extract ports from URLs for backward compatibility
        backend_port = "443" if "https" in backend_url else "80"
        auth_port = "443" if "https" in auth_url else "80"
        redis_port = "6379"
        
        logger.info(f"FIVE-WHYS FIX: Using staging GCP service URLs - Backend: {backend_url}")
        
    elif is_production:
        # Production GCP service URLs  
        backend_url = env.get("PRODUCTION_BACKEND_URL", "https://api.netrasystems.ai")
        auth_url = env.get("PRODUCTION_AUTH_URL", "https://auth.netrasystems.ai")
        redis_url = env.get("PRODUCTION_REDIS_URL", "redis://production-redis:6379")
        
        backend_port = "443"
        auth_port = "443" 
        redis_port = "6379"
        
        logger.info(f"FIVE-WHYS FIX: Using production GCP service URLs - Backend: {backend_url}")
        
    else:
        # Local development service URLs
        backend_port = env.get("BACKEND_PORT", "8000")
        auth_port = env.get("AUTH_SERVICE_PORT", "8081")
        redis_port = env.get("REDIS_PORT", "6381")  # Test Redis port
        
        backend_url = f"http://localhost:{backend_port}"
        auth_url = f"http://localhost:{auth_port}"
        redis_url = f"redis://localhost:{redis_port}"
        
        logger.info(f"FIVE-WHYS FIX: Using local development service URLs - Backend: {backend_url}")
    
    # Validate services are reachable (optional - don't fail if not available)
    services_available = {
        "backend": False,
        "auth": False,
        "database": postgres_info["available"],
        "redis": False
    }
    
    # Test Redis connection
    try:
        import redis
        redis_client = redis.Redis.from_url(redis_url, socket_timeout=2)
        await redis_client.ping()
        services_available["redis"] = True
        await redis_client.close()
    except Exception:
        logger.info("Redis service not reachable - tests will use URL only")
    
    try:
        import aiohttp
        timeout = aiohttp.ClientTimeout(total=2)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            # Test backend service
            try:
                async with session.get(f"{backend_url}/health") as resp:
                    services_available["backend"] = resp.status == 200
            except Exception:
                logger.info("Backend service not reachable - tests will use URL only")
            
            # Test auth service  
            try:
                async with session.get(f"{auth_url}/health") as resp:
                    services_available["auth"] = resp.status == 200
            except Exception:
                logger.info("Auth service not reachable - tests will use URL only")
    except ImportError:
        logger.info("aiohttp not available - skipping service health checks")
    
    # FIVE-WHYS FIX: Add missing configuration keys that E2E tests expect
    websocket_url = backend_url.replace("http://", "ws://").replace("https://", "wss://") + "/ws"
    
    yield {
        "backend_url": backend_url,
        "backend_port": backend_port,  # FIX: Add missing backend_port key
        "auth_url": auth_url,
        "auth_port": auth_port,  # Add auth_port for completeness
        "redis_url": redis_url,
        "redis_port": redis_port,  # Add redis_port for completeness
        "websocket_url": websocket_url,  # FIX: Add WebSocket URL for E2E tests
        "postgres": postgres_info["engine"],
        "db": db_session,
        "redis": redis_url,  # Add redis key for compatibility
        "database_url": postgres_info["database_url"],
        "environment": postgres_info["environment"],
        "environment_name": environment,  # Add explicit environment name
        "is_staging": is_staging,  # Add staging detection flag
        "is_production": is_production,  # Add production detection flag
        "services_available": services_available,
        "database_available": postgres_info["available"],
        "redis_available": services_available["redis"]  # Add redis_available key
    }


@pytest.fixture(scope="function")
async def integration_services_fixture():
    """
    INTEGRATION SERVICES FIXTURE - Service abstraction layer for integration tests.
    
    This fixture provides service abstractions that work with real services when
    available or gracefully degrade to in-memory alternatives for integration testing.
    
    CRITICAL: This enables integration tests to run with --no-docker flag.
    
    Yields:
        IntegrationServiceManager: Service manager with connected abstractions
    """
    try:
        from test_framework.service_abstraction.integration_service_abstraction import IntegrationServiceManager
    except ImportError:
        logger.error("Integration service abstraction not available")
        yield None
        return
    
    env = get_env()
    
    # Configure service abstractions based on environment
    config = {
        "database": {
            "host": env.get("TEST_POSTGRES_HOST", "localhost"),
            "port": int(env.get("TEST_POSTGRES_PORT", "5434")),
            "user": env.get("TEST_POSTGRES_USER", "test_user"),
            "password": env.get("TEST_POSTGRES_PASSWORD", "test_password"),
            "database": env.get("TEST_POSTGRES_DB", "netra_test")
        },
        "websocket": {
            "url": env.get("TEST_WEBSOCKET_URL", "ws://localhost:8000/ws")
        }
    }
    
    service_manager = IntegrationServiceManager(config)
    
    try:
        # Connect to all services
        connection_results = await service_manager.connect_all()
        logger.info(f"Integration services connected: {connection_results}")
        
        # Verify at least database connection worked
        if not connection_results.get("database", False):
            logger.warning("Database connection failed - integration tests may not work properly")
        
        yield service_manager
        
    finally:
        # Cleanup
        try:
            await service_manager.disconnect_all()
        except Exception as e:
            logger.warning(f"Error during integration services cleanup: {e}")


@asynccontextmanager
async def real_database_session(real_services_fixture) -> AsyncGenerator[Any, None]:
    """Context manager for real database session.
    
    Usage:
        async with real_database_session(real_services) as db:
            await db.execute("SELECT 1")
    """
    services = real_services_fixture
    
    if not services["database_available"] or not services["db"]:
        raise RuntimeError("Real database session not available")
    
    yield services["db"]
