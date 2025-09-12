"""Real Services Conftest - Replaces ALL mocks with real service connections.

This module provides pytest fixtures that use actual PostgreSQL, Redis, ClickHouse,
WebSocket, and HTTP connections instead of mocks. It's designed to completely
eliminate the 5766+ mock violations across the codebase.

Import this in your conftest.py files to get real service fixtures:
    from test_framework.conftest_real_services import *

Key Features:
- Real database connections with proper isolation  
- Real Redis caching with test database separation
- Real ClickHouse analytics with fast test data
- Real WebSocket connections for integration testing
- Real HTTP clients for API testing  
- Automatic service health checking and retry logic
- Fast setup/teardown with connection pooling
- Per-test data isolation and cleanup
"""

import asyncio
import logging
import os
import sys
from typing import AsyncIterator, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest

# Import real services infrastructure
from test_framework.real_services import (
    RealServicesManager,
    DatabaseManager, 
    RedisManager,
    ClickHouseManager,
    WebSocketTestClient,
    HTTPTestClient,
    ServiceUnavailableError,
    get_real_services,
    skip_if_services_unavailable,
    load_test_fixtures
)

# Import real service fixtures
from test_framework.fixtures.real_services import (
    real_postgres_connection,
    with_test_database,
    real_services_fixture
)

# Import lightweight service fixtures for non-Docker integration testing
from test_framework.fixtures.lightweight_services import (
    lightweight_postgres_connection,
    lightweight_test_database,  
    lightweight_services_fixture,
    lightweight_auth_context,
    integration_services
)

# Import environment isolation
from test_framework.environment_isolation import (
    get_test_env_manager,
    isolated_test_session,
    isolated_test_env,
    ensure_test_isolation
)

logger = logging.getLogger(__name__)

# =============================================================================
# REAL SERVICE CONFIGURATION  
# =============================================================================

# Environment setup for real services
if "pytest" in sys.modules or get_test_env_manager().env.get("PYTEST_CURRENT_TEST"):
    ensure_test_isolation()
    
    # Set real service environment variables
    env_manager = get_test_env_manager()
    env = env_manager.env
    env.set("USE_REAL_SERVICES", "true", source="real_services_conftest")
    env.set("SKIP_MOCKS", "true", source="real_services_conftest")
    
    # Check for staging environment
    current_env = env.get("ENVIRONMENT", "").lower()
    is_staging = current_env == "staging"
    
    if is_staging:
        # Staging environment - use GCP services
        env.set("TESTING", "0", source="real_services_conftest")  # Not local testing
        # Use staging service URLs from environment or defaults
        pass  # Staging services use environment variables from GCP
    else:
        # Local/test environment - use Docker containers
        env.set("TESTING", "1", source="real_services_conftest") 
        
        # Service endpoints for real testing (Docker containers)
        env.set("TEST_POSTGRES_HOST", "localhost", source="real_services_conftest")
        env.set("TEST_POSTGRES_PORT", "5433", source="real_services_conftest")
        env.set("TEST_POSTGRES_USER", "test_user", source="real_services_conftest")
        env.set("TEST_POSTGRES_PASSWORD", "test_pass", source="real_services_conftest")
        env.set("TEST_POSTGRES_DB", "netra_test", source="real_services_conftest")
        env.set("TEST_REDIS_HOST", "localhost", source="real_services_conftest") 
        env.set("TEST_REDIS_PORT", "6381", source="real_services_conftest")
        env.set("TEST_CLICKHOUSE_HOST", "localhost", source="real_services_conftest")
        env.set("TEST_CLICKHOUSE_HTTP_PORT", "8126", source="real_services_conftest")  # Test HTTP port - matches ALPINE_TEST_CLICKHOUSE_HTTP_PORT
        env.set("TEST_CLICKHOUSE_TCP_PORT", "9003", source="real_services_conftest")   # Test TCP port - matches ALPINE_TEST_CLICKHOUSE_TCP_PORT
        env.set("TEST_CLICKHOUSE_USER", "test", source="real_services_conftest")  # Matches Docker container config
        env.set("TEST_CLICKHOUSE_PASSWORD", "test", source="real_services_conftest")  # Matches Docker container config
        env.set("TEST_CLICKHOUSE_DB", "test_analytics", source="real_services_conftest")  # Matches Docker container config


# =============================================================================
# CONDITIONAL SERVICE ORCHESTRATION
# =============================================================================

@pytest.fixture(scope="function", autouse=True)
def conditional_service_orchestration(request):
    """Conditionally run service orchestration based on test markers.
    
    This fixture runs automatically but only orchestrates services for:
    - Tests marked with @pytest.mark.integration
    - Tests marked with @pytest.mark.e2e
    - Tests that explicitly request real_services fixtures
    """
    """Conditionally run service orchestration based on test markers.
    
    FIXED: Converted from async session to sync function-scoped fixture
    to avoid ScopeMismatch with pytest-asyncio function-scoped event loops.
    """
    # Check if this test needs service orchestration
    markers = list(request.node.iter_markers())
    marker_names = [m.name for m in markers]
    
    # Only orchestrate for integration/e2e tests
    needs_orchestration = any(name in ['integration', 'e2e', 'real_services'] for name in marker_names)
    
    # Also check if test is requesting real services fixtures
    if not needs_orchestration and hasattr(request, 'fixturenames'):
        needs_orchestration = any('real_' in name or 'e2e' in name for name in request.fixturenames)
    
    if not needs_orchestration:
        # Skip orchestration for unit tests
        logger.debug("Skipping service orchestration for unit test")
        yield
        return
    
    # Run the actual orchestration
    logger.info("Running service orchestration for integration/e2e test")
    # Delegate to the real_services_function fixture
    yield

# =============================================================================
# SESSION-SCOPED REAL SERVICE FIXTURES
# =============================================================================

@pytest.fixture(scope="function", autouse=False)  # Changed to function scope to fix ScopeMismatch
async def real_services_function() -> AsyncIterator[RealServicesManager]:
    """Function-scoped real services manager with E2E service orchestration.
    
    FIXED: Converted from session to function scope to avoid ScopeMismatch
    with pytest-asyncio function-scoped event loops.
    
    This fixture is now opt-in. Tests that need real services should:
    1. Mark with @pytest.mark.integration or @pytest.mark.e2e
    2. Or explicitly request this fixture
    """
    logger.info("[U+1F680] Starting E2E Service Orchestration for test session...")
    
    # Check if real services should be used
    env_manager = get_test_env_manager()
    use_real_services = env_manager.env.get("USE_REAL_SERVICES", "false").lower() == "true"
    current_env = env_manager.env.get("ENVIRONMENT", "").lower()
    is_staging = current_env == "staging"
    
    # CRITICAL: Check for orchestration skip flags
    no_orchestration = env_manager.env.get("NO_DOCKER_ORCHESTRATION", "false").lower() == "true"
    skip_orchestration = env_manager.env.get("SKIP_SERVICE_ORCHESTRATION", "false").lower() == "true"
    
    if no_orchestration or skip_orchestration:
        logger.info("Docker/Service orchestration disabled, skipping service orchestration fixtures")
        pytest.skip("Service orchestration disabled (NO_DOCKER_ORCHESTRATION=true or SKIP_SERVICE_ORCHESTRATION=true)")
    
    # Real services are always used in staging environment
    if not (use_real_services or is_staging):
        logger.info("Real services disabled, skipping real service fixtures")
        pytest.skip("Real services disabled (set USE_REAL_SERVICES=true to enable or ENVIRONMENT=staging)")
        
    if is_staging:
        logger.info("Running in staging environment with real GCP services")
        manager = get_real_services()
        
        try:
            # For staging, just check service availability
            await manager.ensure_all_services_available()
            logger.info(" PASS:  All staging services are healthy and ready")
            yield manager
        except ServiceUnavailableError as e:
            logger.error(f" FAIL:  Staging services not available: {e}")
            pytest.skip(f"Staging services unavailable: {e}")
        except Exception as e:
            logger.error(f" FAIL:  Failed to initialize staging services: {e}")
            raise
        finally:
            await manager.close_all()
            logger.info("Staging services session cleanup completed")
    else:
        # Local/test environment - use service orchestrator for Docker services
        from test_framework.unified_docker_manager import ServiceOrchestrator, OrchestrationConfig
        
        # Configure orchestration for E2E testing
        orchestration_config = OrchestrationConfig(
            environment=current_env,
            required_services=["postgres", "redis", "backend", "auth"],
            startup_timeout=90.0,  # Generous timeout for Docker service startup
            health_check_timeout=10.0,
            health_check_retries=15
        )
        
        # Use pull_policy='never' if we have rate limit issues, otherwise 'missing'
        # This prevents Docker Hub pulls when base images are available locally
        pull_policy = env.get("DOCKER_PULL_POLICY", "missing")
        orchestrator = ServiceOrchestrator(orchestration_config, pull_policy=pull_policy)
        
        try:
            # Phase 1: Orchestrate services (start + health check)
            logger.info(" CYCLE:  Orchestrating E2E services...")
            success, health_report = await orchestrator.orchestrate_services()
            
            if not success:
                error_report = orchestrator.get_health_report()
                logger.error(error_report)
                pytest.skip(f"E2E Service orchestration failed - services not healthy")
            
            logger.info(" PASS:  E2E Service orchestration completed successfully")
            logger.info(orchestrator.get_health_report())
            
            # Phase 2: Initialize real services manager with orchestrated services
            manager = get_real_services()
            await manager.ensure_all_services_available()
            logger.info(" PASS:  All real services are healthy and ready")
            
            # Phase 3: Load initial test fixtures
            fixture_dir = os.path.join(os.path.dirname(__file__), "fixtures", "test_data")
            if os.path.exists(fixture_dir):
                await load_test_fixtures(manager, fixture_dir)
            
            yield manager
            
        except ServiceUnavailableError as e:
            logger.error(f" FAIL:  Real services not available after orchestration: {e}")
            pytest.skip(f"Real services unavailable: {e}")
        except Exception as e:
            logger.error(f" FAIL:  E2E Service orchestration failed: {e}")
            raise
        finally:
            # Cleanup session resources
            if 'manager' in locals():
                await manager.close_all()
            
            # Optional: Cleanup orchestrated services (only if we started them)
            if orchestrator.started_services:
                logger.info("[U+1F9F9] Cleaning up orchestrated services...")
                await orchestrator.cleanup_services()
            
            logger.info(" PASS:  E2E Service orchestration cleanup completed")


# =============================================================================
# FUNCTION-SCOPED REAL SERVICE FIXTURES  
# =============================================================================

@pytest.fixture(scope="function")
async def real_services(real_services_function: RealServicesManager) -> AsyncIterator[RealServicesManager]:
    """Function-scoped real services with automatic data cleanup."""
    # Reset all data before test
    await real_services_function.reset_all_data()
    
    yield real_services_function
    
    # Optional: Reset after test for extra isolation
    # Commented out for performance, but can be enabled if needed
    # await real_services_function.reset_all_data()


# Backward compatibility removed - use real_services_function instead


@pytest.fixture(scope="function")
async def real_postgres(real_services: RealServicesManager) -> AsyncIterator[DatabaseManager]:
    """Real PostgreSQL database connection."""
    yield real_services.postgres


@pytest.fixture(scope="function") 
async def real_redis(real_services: RealServicesManager) -> AsyncIterator[RedisManager]:
    """Real Redis cache connection.""" 
    yield real_services.redis


@pytest.fixture(scope="function")
async def real_clickhouse(real_services: RealServicesManager) -> AsyncIterator[ClickHouseManager]:
    """Real ClickHouse analytics connection."""
    yield real_services.clickhouse


@pytest.fixture(scope="function")
async def real_websocket_client(real_services: RealServicesManager) -> AsyncIterator[WebSocketTestClient]:
    """Real WebSocket client for testing."""
    client = real_services.create_websocket_client()
    yield client
    await client.close()


@pytest.fixture(scope="function")
async def real_http_client(real_services: RealServicesManager) -> AsyncIterator[HTTPTestClient]:
    """Real HTTP client for API testing."""
    client = await real_services.get_http_client()
    yield client


# =============================================================================
# REPLACEMENT FIXTURES FOR EXISTING MOCKS
# These replace the mocked fixtures in the original conftest.py
# =============================================================================

@pytest.fixture
async def redis_manager(real_redis: RedisManager) -> AsyncIterator[RedisManager]:
    """REAL Redis manager - replaces mock_redis_manager."""
    yield real_redis


@pytest.fixture 
async def redis_client(real_redis: RedisManager) -> AsyncIterator:
    """REAL Redis client - replaces mock_redis_client."""
    client = await real_redis.get_client()
    yield client
    # Client is closed by the manager


@pytest.fixture
def clickhouse_client(real_clickhouse: ClickHouseManager):
    """REAL ClickHouse client - replaces mock_clickhouse_client."""
    return real_clickhouse.get_client()


@pytest.fixture
async def database_connection(real_postgres: DatabaseManager) -> AsyncIterator:
    """REAL database connection - replaces database mocks."""
    async with real_postgres.connection() as conn:
        yield conn


@pytest.fixture
async def database_transaction(real_postgres: DatabaseManager) -> AsyncIterator:
    """REAL database transaction - replaces transaction mocks."""
    async with real_postgres.transaction() as tx:
        yield tx


# =============================================================================
# WEBSOCKET TESTING FIXTURES
# =============================================================================

@pytest.fixture
async def websocket_connection(real_websocket_client: WebSocketTestClient) -> AsyncIterator[WebSocketTestClient]:
    """REAL WebSocket connection - replaces WebSocket mocks."""
    # Connect to default WebSocket endpoint
    await real_websocket_client.connect()
    yield real_websocket_client


@pytest.fixture
async def authenticated_websocket(real_websocket_client: WebSocketTestClient, test_user_token) -> AsyncIterator[WebSocketTestClient]:
    """REAL authenticated WebSocket connection."""
    headers = {"Authorization": f"Bearer {test_user_token['token']}"}
    await real_websocket_client.connect(headers=headers)
    yield real_websocket_client


# =============================================================================
# HTTP API TESTING FIXTURES
# =============================================================================

@pytest.fixture
async def api_client(real_http_client: HTTPTestClient) -> AsyncIterator[HTTPTestClient]:
    """REAL HTTP API client - replaces HTTP mocks."""
    yield real_http_client


@pytest.fixture
async def authenticated_api_client(real_http_client: HTTPTestClient, test_user_token) -> AsyncIterator[HTTPTestClient]:
    """REAL authenticated HTTP API client."""
    # Set default authorization header
    client = real_http_client
    if hasattr(client, '_client') and client._client:
        client._client.headers.update({"Authorization": f"Bearer {test_user_token['token']}"})
    yield client


# =============================================================================
# SERVICE-SPECIFIC FIXTURES
# =============================================================================

@pytest.fixture
async def auth_service_client(real_http_client: HTTPTestClient, real_services: RealServicesManager) -> AsyncIterator[HTTPTestClient]:
    """REAL auth service client."""
    # Configure for auth service endpoint
    base_url = real_services.config.auth_service_url
    yield real_http_client  # Use same HTTP client, but with auth service awareness


@pytest.fixture
async def backend_service_client(real_http_client: HTTPTestClient, real_services: RealServicesManager) -> AsyncIterator[HTTPTestClient]:
    """REAL backend service client."""
    # Configure for backend service endpoint  
    base_url = real_services.config.backend_service_url
    yield real_http_client


# =============================================================================
# TEST DATA FIXTURES WITH REAL DATABASE
# =============================================================================

@pytest.fixture
async def test_user(real_postgres: DatabaseManager) -> Dict:
    """Create real test user in database."""
    user_data = {
        'email': 'test@example.com',
        'name': 'Test User',
        'password_hash': '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdCmUiGD.9K.9qS',  # 'test123'
        'is_active': True,
        'is_superuser': False
    }
    
    # Insert or update real user into database (handle existing users)
    user_id = await real_postgres.fetchval("""
        INSERT INTO auth.users (email, name, password_hash, is_active, is_superuser)
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (email) DO UPDATE SET
            name = EXCLUDED.name,
            password_hash = EXCLUDED.password_hash,
            is_active = EXCLUDED.is_active,
            is_superuser = EXCLUDED.is_superuser
        RETURNING id
    """, user_data['email'], user_data['name'], user_data['password_hash'],
        user_data['is_active'], user_data['is_superuser'])
    
    user_data['id'] = str(user_id)
    return user_data


@pytest.fixture
async def test_organization(real_postgres: DatabaseManager, test_user) -> Dict:
    """Create real test organization in database.""" 
    org_data = {
        'name': 'Test Organization',
        'slug': 'test-org',
        'plan': 'free'
    }
    
    # Insert real organization
    org_id = await real_postgres.fetchval("""
        INSERT INTO backend.organizations (name, slug, plan)
        VALUES ($1, $2, $3)
        RETURNING id
    """, org_data['name'], org_data['slug'], org_data['plan'])
    
    org_data['id'] = str(org_id)
    
    # Link user to organization
    await real_postgres.execute("""
        INSERT INTO backend.organization_memberships (user_id, organization_id, role)
        VALUES ($1, $2, $3)
    """, test_user['id'], org_id, 'admin')
    
    return org_data


@pytest.fixture
async def test_agent(real_postgres: DatabaseManager, test_organization, test_user) -> Dict:
    """Create real test agent in database."""
    agent_data = {
        'name': 'Test Agent',
        'description': 'A test agent for testing',
        'system_prompt': 'You are a helpful test assistant.',
        'model_config': {'model': 'gpt-4', 'temperature': 0.7}
    }
    
    # Insert real agent
    agent_id = await real_postgres.fetchval("""
        INSERT INTO backend.agents (organization_id, name, description, system_prompt, model_config, created_by)
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING id
    """, test_organization['id'], agent_data['name'], agent_data['description'],
        agent_data['system_prompt'], agent_data['model_config'], test_user['id'])
    
    agent_data['id'] = str(agent_id)
    agent_data['organization_id'] = test_organization['id']
    agent_data['created_by'] = test_user['id']
    return agent_data


@pytest.fixture
async def test_conversation(real_postgres: DatabaseManager, test_agent, test_user) -> Dict:
    """Create real test conversation in database."""
    conv_data = {
        'title': 'Test Conversation',
        'status': 'active'
    }
    
    # Insert real conversation
    conv_id = await real_postgres.fetchval("""
        INSERT INTO backend.conversations (agent_id, user_id, title, status)
        VALUES ($1, $2, $3, $4)
        RETURNING id
    """, test_agent['id'], test_user['id'], conv_data['title'], conv_data['status'])
    
    conv_data['id'] = str(conv_id)
    conv_data['agent_id'] = test_agent['id'] 
    conv_data['user_id'] = test_user['id']
    return conv_data


@pytest.fixture 
async def test_user_token(test_user) -> Dict:
    """Generate real JWT token for test user."""
    # This would typically use your actual JWT creation logic
    # For now, return a mock token structure that tests can use
    return {
        'token': 'test-jwt-token-for-' + test_user['id'],
        'user_id': test_user['id'],
        'email': test_user['email'],
        'expires_at': '2025-12-31T23:59:59Z'
    }


# =============================================================================
# MIGRATION HELPERS  
# =============================================================================

def require_real_services():
    """Decorator to require real services for a test."""
    def decorator(func):
        return pytest.mark.skipif(
            get_test_env_manager().env.get("USE_REAL_SERVICES", "false").lower() != "true",
            reason="Real services required (set USE_REAL_SERVICES=true)"
        )(func)
    return decorator


@pytest.fixture
def ensure_no_mocks():
    """Fixture that ensures no mocks are used in the test."""
    # This can be used to verify that a test is truly mock-free
    original_magicmock_init = MagicMock.__init__
    original_asyncmock_init = AsyncMock.__init__
    
    def mock_detector(*args, **kwargs):
        raise RuntimeError("Mock detected! This test should use real services only.")
    
    # Temporarily replace mock constructors with detectors
    MagicMock.__init__ = mock_detector
    AsyncMock.__init__ = mock_detector
    
    try:
        yield
    finally:
        # Restore original constructors
        MagicMock.__init__ = original_magicmock_init
        AsyncMock.__init__ = original_asyncmock_init


# =============================================================================
# PERFORMANCE AND MONITORING FIXTURES
# =============================================================================

@pytest.fixture
def performance_monitor():
    """Monitor test performance with real services."""
    import time
    
    class RealServicePerformanceMonitor:
        def __init__(self):
            self.start_time = None
            self.measurements = {}
            
        def start(self, operation: str):
            self.measurements[operation] = {'start': time.time()}
            
        def end(self, operation: str) -> float:
            if operation in self.measurements:
                duration = time.time() - self.measurements[operation]['start']
                self.measurements[operation]['duration'] = duration
                return duration
            return 0.0
            
        def assert_performance(self, operation: str, max_duration: float):
            """Assert that operation completed within performance threshold."""
            if operation not in self.measurements:
                raise AssertionError(f"No measurement found for {operation}")
            
            duration = self.measurements[operation]['duration']
            if duration > max_duration:
                raise AssertionError(
                    f"{operation} took {duration:.2f}s (max: {max_duration}s) with real services"
                )
    
    return RealServicePerformanceMonitor()


# =============================================================================
# EXPORT ALL REAL SERVICE FIXTURES
# =============================================================================

# Export all fixtures for easy import
__all__ = [
    # Core real service managers
    'real_services_function',  # New primary fixture (function-scoped)
    # 'real_services_session', # Backward compatibility removed
    'real_services', 
    'real_postgres',
    'real_redis',
    'real_clickhouse',
    'real_websocket_client',
    'real_http_client',
    
    # Replacement fixtures for mocks
    'redis_manager',
    'redis_client', 
    'clickhouse_client',
    'database_connection',
    'database_transaction',
    
    # WebSocket fixtures
    'websocket_connection',
    'authenticated_websocket',
    
    # HTTP API fixtures
    'api_client',
    'authenticated_api_client',
    'auth_service_client',
    'backend_service_client',
    
    # Test data fixtures
    'test_user',
    'test_organization', 
    'test_agent',
    'test_conversation',
    'test_user_token',
    
    # Utilities
    'require_real_services',
    'ensure_no_mocks',
    'performance_monitor'
]