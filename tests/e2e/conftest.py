"""
E2E Test Configuration and Fixtures

Provides specialized fixtures and configuration for end-to-end testing
with real services. Ensures proper setup, teardown, and environment
validation for comprehensive E2E test execution.

Business Value: Enables reliable E2E testing that validates production readiness
"""

import pytest
import asyncio
import os
import logging
import time
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager

# Configure E2E test logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("e2e_conftest")

# E2E Test Environment Configuration
E2E_CONFIG = {
    "auth_service_url": os.getenv("E2E_AUTH_SERVICE_URL", "http://localhost:8001"),
    "backend_url": os.getenv("E2E_BACKEND_URL", "http://localhost:8000"),
    "websocket_url": os.getenv("E2E_WEBSOCKET_URL", "ws://localhost:8000/ws"),
    "redis_url": os.getenv("E2E_REDIS_URL", "redis://localhost:6379"),
    "postgres_url": os.getenv("E2E_POSTGRES_URL", "postgresql://postgres:netra@localhost:5432/netra_test"),
    "clickhouse_url": os.getenv("E2E_CLICKHOUSE_URL", "clickhouse://localhost:8123/netra_test"),
    "test_timeout": int(os.getenv("E2E_TEST_TIMEOUT", "300")),  # 5 minutes
    "performance_mode": os.getenv("E2E_PERFORMANCE_MODE", "true").lower() == "true"
}


class E2EEnvironmentValidator:
    """Validates E2E test environment prerequisites."""
    
    @staticmethod
    async def validate_services_available() -> Dict[str, bool]:
        """Validate that all required services are available."""
        import httpx
        import redis
        import asyncpg
        
        service_status = {}
        
        # Check Auth Service
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{E2E_CONFIG['auth_service_url']}/health", timeout=10.0)
                service_status["auth_service"] = response.status_code == 200
        except Exception:
            service_status["auth_service"] = False
        
        # Check Backend Service
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{E2E_CONFIG['backend_url']}/health", timeout=10.0)
                service_status["backend"] = response.status_code == 200
        except Exception:
            service_status["backend"] = False
        
        # Check Redis
        try:
            redis_client = redis.Redis.from_url(E2E_CONFIG["redis_url"], decode_responses=True)
            await redis_client.ping()
            service_status["redis"] = True
            await redis_client.aclose() if hasattr(redis_client, 'aclose') else None
        except Exception:
            service_status["redis"] = False
        
        # Check PostgreSQL
        try:
            conn = await asyncpg.connect(E2E_CONFIG["postgres_url"])
            await conn.fetchval("SELECT 1")
            service_status["postgres"] = True
            await conn.close()
        except Exception:
            service_status["postgres"] = False
        
        return service_status
    
    @staticmethod
    def validate_environment_variables() -> Dict[str, bool]:
        """Validate required environment variables are set."""
        required_vars = [
            "GOOGLE_API_KEY",  # For real LLM testing
            "JWT_SECRET_KEY",  # For authentication
            "FERNET_KEY"       # For encryption
        ]
        
        var_status = {}
        for var in required_vars:
            var_status[var] = os.getenv(var) is not None
            
        return var_status


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    # Don't close the loop to avoid hanging


@pytest.fixture(scope="session")
async def validate_e2e_environment():
    """Validate E2E test environment before running tests."""
    logger.info("Validating E2E test environment...")
    
    # Skip E2E tests if not explicitly enabled
    if not os.getenv("RUN_E2E_TESTS", "false").lower() == "true":
        pytest.skip("E2E tests disabled (set RUN_E2E_TESTS=true to enable)")
    
    validator = E2EEnvironmentValidator()
    
    # Validate services
    service_status = await validator.validate_services_available()
    failed_services = [name for name, status in service_status.items() if not status]
    
    if failed_services:
        pytest.skip(f"Required services unavailable: {failed_services}")
    
    # Validate environment variables
    env_status = validator.validate_environment_variables()
    missing_vars = [var for var, status in env_status.items() if not status]
    
    if missing_vars:
        pytest.skip(f"Required environment variables missing: {missing_vars}")
    
    logger.info("E2E environment validation passed")
    return {
        "services": service_status,
        "environment": env_status,
        "config": E2E_CONFIG
    }


@pytest.fixture
async def e2e_test_context(validate_e2e_environment):
    """Provide E2E test context with validated environment."""
    from .test_real_services_e2e import RealServiceE2ETestSuite
    
    suite = RealServiceE2ETestSuite()
    
    try:
        await suite.setup_test_environment()
        
        class E2EContext:
            def __init__(self):
                self.suite = suite
                self.config = E2E_CONFIG
                self.start_time = time.time()
                
            def get_performance_report(self):
                return suite.generate_performance_report()
        
        context = E2EContext()
        yield context
        
    finally:
        await suite.teardown_test_environment()
        
        # Log test duration
        duration = time.time() - context.start_time
        logger.info(f"E2E test context cleanup completed in {duration:.2f}s")


@pytest.fixture
def performance_monitor():
    """Monitor test performance and validate against requirements."""
    from . import PERFORMANCE_REQUIREMENTS
    
    class PerformanceMonitor:
        def __init__(self):
            self.requirements = PERFORMANCE_REQUIREMENTS
            self.measurements = {}
            
        def start_measurement(self, operation: str):
            self.measurements[operation] = {"start": time.time()}
            
        def end_measurement(self, operation: str):
            if operation in self.measurements:
                self.measurements[operation]["duration"] = time.time() - self.measurements[operation]["start"]
                
        def validate_requirement(self, operation: str, max_duration: float = None):
            if operation not in self.measurements:
                raise ValueError(f"No measurement found for operation: {operation}")
                
            duration = self.measurements[operation]["duration"]
            max_allowed = max_duration or self.requirements.get(f"{operation}_max", 10.0)
            
            if duration > max_allowed:
                raise AssertionError(f"{operation} took {duration:.2f}s (max: {max_allowed}s)")
                
            return duration
    
    return PerformanceMonitor()


@pytest.fixture
def e2e_logger():
    """Provide specialized E2E test logger."""
    logger = logging.getLogger("e2e_test")
    logger.setLevel(logging.INFO)
    
    class E2ELogger:
        def __init__(self, base_logger):
            self.logger = base_logger
            
        def test_start(self, test_name: str):
            self.logger.info(f"[START] {test_name}")
            
        def test_success(self, test_name: str, duration: float):
            self.logger.info(f"[SUCCESS] {test_name} completed in {duration:.2f}s")
            
        def test_failure(self, test_name: str, error: str):
            self.logger.error(f"[FAILURE] {test_name} failed: {error}")
            
        def performance_metric(self, operation: str, duration: float, limit: float):
            status = "PASS" if duration <= limit else "FAIL"
            self.logger.info(f"[PERF-{status}] {operation}: {duration:.2f}s (limit: {limit}s)")
            
        def business_impact(self, message: str):
            self.logger.info(f"[BUSINESS] {message}")
    
    return E2ELogger(logger)


@pytest.fixture(autouse=True)
def setup_e2e_test_environment():
    """Auto-setup E2E test environment variables."""
    os.environ["TESTING"] = "1"
    os.environ["NETRA_ENV"] = "e2e_testing" 
    os.environ["USE_REAL_SERVICES"] = "true"
    os.environ["AUTH_FAST_TEST_MODE"] = "true"
    
    # Set longer timeouts for E2E tests
    os.environ["HTTP_TIMEOUT"] = "30"
    os.environ["WEBSOCKET_TIMEOUT"] = "30"
    os.environ["LLM_TIMEOUT"] = "60"


# Performance test decorators
def requires_cold_start_performance(max_seconds: float = 5.0):
    """Decorator to enforce cold start performance requirements."""
    def decorator(func):
        func._performance_requirement = ("cold_start", max_seconds)
        return func
    return decorator


def requires_sync_performance(max_seconds: float = 2.0):
    """Decorator to enforce synchronization performance requirements."""
    def decorator(func):
        func._performance_requirement = ("sync", max_seconds)
        return func
    return decorator


def requires_llm_performance(max_seconds: float = 10.0):
    """Decorator to enforce LLM response performance requirements."""
    def decorator(func):
        func._performance_requirement = ("llm", max_seconds)
        return func
    return decorator


# Throughput testing fixtures
@pytest.fixture
async def high_volume_server():
    """High-volume WebSocket server fixture for throughput testing."""
    from .test_helpers.high_volume_server import HighVolumeWebSocketServer
    
    # Skip if not in mock test mode
    if os.getenv("HIGH_VOLUME_TEST_MODE", "mock") != "mock":
        yield None
        return
        
    server = HighVolumeWebSocketServer()
    await server.start()
    
    # Allow server startup time
    await asyncio.sleep(1.0)
    
    yield server
    await server.stop()


@pytest.fixture
async def test_user_token():
    """Create test user and return auth token for throughput testing."""
    import uuid
    import httpx
    
    if os.getenv("HIGH_VOLUME_TEST_MODE", "mock") == "real":
        # Use real authentication service
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{E2E_CONFIG['auth_service_url']}/auth/test-user",
                    json={"email": f"throughput-test-{uuid.uuid4().hex[:8]}@example.com"},
                    timeout=10.0
                )
                if response.status_code == 200:
                    token_data = response.json()
                    return {
                        "user_id": token_data["user_id"],
                        "token": token_data["token"],
                        "email": token_data["email"]
                    }
        except Exception as e:
            logger.warning(f"Real auth failed, using mock: {e}")
    
    # Fallback to mock authentication
    test_user_id = f"throughput-user-{uuid.uuid4().hex[:8]}"
    return {
        "user_id": test_user_id,
        "token": f"mock-token-{uuid.uuid4().hex}",
        "email": f"{test_user_id}@example.com"
    }


@pytest.fixture
async def throughput_client(test_user_token, high_volume_server):
    """High-volume throughput client fixture."""
    from .test_helpers.high_volume_server import HighVolumeThroughputClient
    
    websocket_uri = os.getenv("E2E_WEBSOCKET_URL", "ws://localhost:8765")
    client = HighVolumeThroughputClient(websocket_uri, test_user_token["token"], "primary-client")
    
    # Establish connection with retry logic
    max_retries = 3
    for attempt in range(max_retries):
        try:
            await client.connect()
            break
        except Exception as e:
            if attempt == max_retries - 1:
                pytest.skip(f"WebSocket connection failed after {max_retries} attempts: {e}")
            await asyncio.sleep(1.0)
    
    yield client
    
    # Cleanup
    try:
        await client.disconnect()
    except Exception as e:
        logger.warning(f"Client cleanup error: {e}")


# Pytest markers for E2E tests
pytest.mark.e2e = pytest.mark.e2e
pytest.mark.real_services = pytest.mark.real_services
pytest.mark.performance = pytest.mark.performance
pytest.mark.critical = pytest.mark.critical
pytest.mark.throughput = pytest.mark.throughput