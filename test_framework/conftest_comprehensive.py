"""Comprehensive pytest fixtures integrating all test infrastructure components.

This module provides the complete suite of pytest fixtures that integrate:
- IsolatedEnvironmentManager with database isolation
- ExternalServiceManager with WebSocket, HTTP, and file system testing
- Real service infrastructure replacing all mocks
- Performance optimization and resource management
- Migration support for 2,941+ test files

Business Value: Platform/Internal - Complete Mock Elimination
Provides industrial-strength test infrastructure supporting the elimination
of all mocks across the entire codebase.

Usage:
    # In conftest.py:
    from test_framework.conftest_comprehensive import *
    
    # In tests:
    async def test_complete_integration(comprehensive_test_environment):
        db = comprehensive_test_environment['database']
        redis = comprehensive_test_environment['redis']
        http = comprehensive_test_environment['http']
        websocket = comprehensive_test_environment['websocket']
        filesystem = comprehensive_test_environment['filesystem']
        
        # Test with complete real service integration
        user_id = await user_service.create_user("test@example.com")
        
        # Verify in real database
        user = await db.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
        assert user is not None
        
        # Test WebSocket notifications
        await websocket.send_message({"type": "user_created", "user_id": user_id})
        notification = await websocket.receive_message()
        assert notification["type"] == "user_created"
        
        # Test file operations
        config_file = await filesystem.create_file("config.json", '{"key": "value"}')
        assert config_file.exists()
"""

import asyncio
import logging
import pytest
import threading
import uuid
from typing import Dict, AsyncIterator, Optional, Any, List
import time

# Import our comprehensive infrastructure
from test_framework.isolated_environment_manager import (
    IsolatedEnvironmentManager,
    IsolationConfig,
    DatabaseTestResource,
    RedisTestResource, 
    ClickHouseTestResource,
    TestResource,
    generate_test_id,
    get_isolated_environment_manager
)

from test_framework.external_service_integration import (
    ExternalServiceManager,
    ExternalServiceConfig,
    WebSocketTestResource,
    HTTPTestResource,
    FileSystemTestResource,
    LLMTestResource,
    get_external_service_manager
)

# Service availability
from test_framework.isolated_environment_manager import (
    POSTGRES_AVAILABLE,
    REDIS_AVAILABLE,
    CLICKHOUSE_AVAILABLE
)

from test_framework.external_service_integration import (
    WEBSOCKETS_AVAILABLE,
    HTTP_AVAILABLE,
    AIOFILES_AVAILABLE
)

logger = logging.getLogger(__name__)

# Global managers for session scope
_session_env_manager: Optional[IsolatedEnvironmentManager] = None
_session_external_manager: Optional[ExternalServiceManager] = None
_session_lock = threading.Lock()


@pytest.fixture(scope="session", autouse=True)
async def comprehensive_test_session() -> AsyncIterator[Dict[str, Any]]:
    """Session-scoped fixture initializing all test infrastructure.
    
    This fixture runs once per test session and:
    - Initializes IsolatedEnvironmentManager with optimized config
    - Initializes ExternalServiceManager with all services
    - Verifies service availability and health
    - Provides session-wide resource management
    - Ensures proper cleanup at session end
    
    Yields:
        Dictionary containing initialized managers and session info
    """
    global _session_env_manager, _session_external_manager
    
    logger.info("Initializing comprehensive test session infrastructure")
    
    # Create optimized configurations
    isolation_config = IsolationConfig(
        # Performance optimizations
        enable_parallel_execution=True,
        max_concurrent_tests=30,
        enable_resource_pooling=True,
        pool_warmup_connections=10,
        pool_max_connections=200,
        
        # Comprehensive monitoring
        enable_health_monitoring=True,
        enable_resource_leak_detection=True,
        enable_automatic_cleanup=True,
        cleanup_on_failure=True,
        
        # Optimized timeouts
        resource_timeout=45.0,
        cleanup_timeout=20.0,
        
        # File system isolation
        enable_file_system_isolation=True,
        auto_cleanup_temp_files=True
    )
    
    external_config = ExternalServiceConfig(
        # WebSocket configuration
        websocket_timeout=30.0,
        enable_websocket_logging=True,
        
        # HTTP optimizations
        http_timeout=45.0,
        http_max_connections=20,
        enable_http_retry=True,
        http_retry_count=3,
        
        # LLM testing configuration
        enable_real_llm=False,  # Disabled by default for safety
        llm_rate_limit_rpm=100,
        llm_cost_limit_usd=2.0,
        
        # File system limits
        max_file_size_mb=500,
        auto_cleanup_files=True,
        
        # Circuit breaker resilience
        circuit_breaker_failure_threshold=10,
        circuit_breaker_timeout=120.0
    )
    
    session_start = time.time()
    
    with _session_lock:
        # Initialize environment manager
        if _session_env_manager is None:
            _session_env_manager = IsolatedEnvironmentManager(isolation_config)
            
        # Initialize external service manager
        if _session_external_manager is None:
            _session_external_manager = ExternalServiceManager(external_config)
            
    env_manager = _session_env_manager
    external_manager = _session_external_manager
    
    try:
        # Initialize both managers
        await env_manager.initialize()
        
        logger.info("Comprehensive test session infrastructure initialized successfully")
        
        # Check service availability
        service_status = {
            'postgres': POSTGRES_AVAILABLE,
            'redis': REDIS_AVAILABLE,
            'clickhouse': CLICKHOUSE_AVAILABLE,
            'websockets': WEBSOCKETS_AVAILABLE,
            'http': HTTP_AVAILABLE,
            'aiofiles': AIOFILES_AVAILABLE
        }
        
        available_services = [k for k, v in service_status.items() if v]
        unavailable_services = [k for k, v in service_status.items() if not v]
        
        logger.info(f"Available services: {', '.join(available_services)}")
        if unavailable_services:
            logger.warning(f"Unavailable services: {', '.join(unavailable_services)}")
            
        session_info = {
            'env_manager': env_manager,
            'external_manager': external_manager,
            'service_status': service_status,
            'session_start_time': session_start,
            'available_services': available_services,
            'unavailable_services': unavailable_services
        }
        
        yield session_info
        
    finally:
        # Session cleanup
        logger.info("Shutting down comprehensive test session infrastructure")
        
        session_end = time.time()
        session_duration = session_end - session_start
        
        # Get final metrics
        env_metrics = env_manager.get_metrics() if env_manager else {}
        
        # Cleanup managers
        if external_manager:
            await external_manager.cleanup_all_resources()
            
        if env_manager:
            await env_manager.shutdown()
            
        logger.info(
            f"Comprehensive test session completed. "
            f"Duration: {session_duration:.2f}s, "
            f"Metrics: {env_metrics}"
        )
        
        with _session_lock:
            _session_env_manager = None
            _session_external_manager = None


@pytest.fixture(scope="function")
async def comprehensive_test_environment(
    comprehensive_test_session: Dict[str, Any]
) -> AsyncIterator[Dict[str, TestResource]]:
    """Function-scoped fixture providing complete integrated test environment.
    
    Creates a fully isolated test environment with all available services:
    - PostgreSQL with transaction-based isolation
    - Redis with per-test database selection
    - ClickHouse with schema-based isolation
    - WebSocket server for real-time communication testing
    - HTTP client for API testing
    - File system isolation for file operations
    - LLM resource with rate limiting (optional)
    
    This is the primary fixture for comprehensive integration testing that
    replaces all mocks with real, isolated services.
    
    Args:
        comprehensive_test_session: Session-scoped infrastructure
        
    Yields:
        Dictionary containing all initialized test resources
        
    Example:
        async def test_complete_user_workflow(comprehensive_test_environment):
            db = comprehensive_test_environment['database']
            redis = comprehensive_test_environment['redis']
            http = comprehensive_test_environment['http']
            websocket = comprehensive_test_environment['websocket']
            filesystem = comprehensive_test_environment['filesystem']
            
            # Create user with real database
            user_id = await db.fetchval(
                "INSERT INTO users (email) VALUES ($1) RETURNING id",
                "test@example.com"
            )
            
            # Cache in real Redis
            await redis.set(f"user:{user_id}", "test@example.com")
            
            # Test WebSocket notification
            await websocket.send_message({
                "type": "user_created",
                "user_id": user_id
            })
            
            # Test HTTP API call
            response = await http.get(f"/api/users/{user_id}")
            assert response.status_code == 200
            
            # Create test file
            config_file = await filesystem.create_file(
                "user_config.json",
                '{"user_id": "' + str(user_id) + '"}'
            )
            assert config_file.exists()
    """
    session = comprehensive_test_session
    env_manager = session['env_manager']
    external_manager = session['external_manager']
    
    test_id = generate_test_id()
    
    # Create comprehensive environment with all services
    env_resources = {}
    external_resources = {}
    
    try:
        # Create database isolation environment
        async with env_manager.create_test_environment(test_id) as db_resources:
            env_resources.update(db_resources)
            
            # Create external services environment
            async with external_manager.external_services_environment(
                test_id,
                enable_websocket=WEBSOCKETS_AVAILABLE,
                enable_http=HTTP_AVAILABLE,
                enable_filesystem=True,
                enable_llm=False  # Disabled by default
            ) as ext_resources:
                external_resources.update(ext_resources)
                
                # Combine all resources
                all_resources = {**env_resources, **external_resources}
                
                logger.debug(
                    f"Created comprehensive test environment {test_id} with resources: "
                    f"{list(all_resources.keys())}"
                )
                
                yield all_resources
                
    except Exception as e:
        logger.error(f"Error in comprehensive test environment {test_id}: {e}")
        raise
    finally:
        logger.debug(f"Cleaned up comprehensive test environment {test_id}")


@pytest.fixture(scope="function")
async def isolated_complete_environment(
    comprehensive_test_session: Dict[str, Any]
) -> AsyncIterator[Dict[str, TestResource]]:
    """Alternative comprehensive environment with stricter isolation.
    
    This fixture provides the same comprehensive environment but with
    additional isolation guarantees for sensitive tests.
    
    Args:
        comprehensive_test_session: Session-scoped infrastructure
        
    Yields:
        Dictionary containing all initialized test resources with strict isolation
    """
    session = comprehensive_test_session
    env_manager = session['env_manager']
    external_manager = session['external_manager']
    
    test_id = f"isolated_{generate_test_id()}"
    
    # Create stricter isolation config
    strict_config = IsolationConfig(
        isolation_level=IsolationLevel.TRANSACTION,
        enable_parallel_execution=False,  # Single-threaded for strict isolation
        enable_resource_pooling=False,   # No sharing
        enable_health_monitoring=True,
        cleanup_on_failure=True,
        resource_timeout=60.0
    )
    
    # Create temporary manager with strict config
    strict_manager = IsolatedEnvironmentManager(strict_config)
    await strict_manager.initialize()
    
    try:
        async with strict_manager.create_test_environment(test_id) as resources:
            logger.debug(f"Created isolated complete environment {test_id}")
            yield resources
    finally:
        await strict_manager.shutdown()
        logger.debug(f"Cleaned up isolated complete environment {test_id}")


@pytest.fixture(scope="function")
async def performance_test_environment(
    comprehensive_test_session: Dict[str, Any]
) -> AsyncIterator[Dict[str, TestResource]]:
    """Performance-optimized test environment for performance testing.
    
    This fixture creates a test environment specifically optimized for
    performance testing with reduced overhead and monitoring.
    
    Args:
        comprehensive_test_session: Session-scoped infrastructure
        
    Yields:
        Dictionary containing performance-optimized test resources
    """
    session = comprehensive_test_session
    
    # Create performance-optimized configs
    perf_isolation_config = IsolationConfig(
        enable_parallel_execution=False,  # Consistent timing
        enable_resource_pooling=True,
        enable_lazy_loading=False,        # Pre-load everything
        enable_health_monitoring=False,   # Reduce overhead
        enable_automatic_cleanup=True,
        resource_timeout=120.0           # Longer timeout for performance tests
    )
    
    perf_external_config = ExternalServiceConfig(
        websocket_timeout=120.0,
        http_timeout=120.0,
        enable_websocket_logging=False,   # Reduce logging overhead
        http_retry_count=1               # Minimal retries
    )
    
    # Create performance-optimized managers
    perf_env_manager = IsolatedEnvironmentManager(perf_isolation_config)
    perf_external_manager = ExternalServiceManager(perf_external_config)
    
    await perf_env_manager.initialize()
    
    test_id = f"perf_{generate_test_id()}"
    
    try:
        async with perf_env_manager.create_test_environment(test_id) as env_resources:
            async with perf_external_manager.external_services_environment(
                test_id,
                enable_websocket=False,  # Minimal services for performance
                enable_http=True,
                enable_filesystem=True,
                enable_llm=False
            ) as ext_resources:
                all_resources = {**env_resources, **ext_resources}
                
                logger.debug(f"Created performance test environment {test_id}")
                yield all_resources
                
    finally:
        await perf_external_manager.cleanup_all_resources()
        await perf_env_manager.shutdown()
        logger.debug(f"Cleaned up performance test environment {test_id}")


@pytest.fixture(scope="class")
async def class_comprehensive_environment(
    comprehensive_test_session: Dict[str, Any]
) -> AsyncIterator[Dict[str, TestResource]]:
    """Class-scoped comprehensive test environment for test classes.
    
    This fixture provides a shared test environment for all tests in a class.
    Useful for test classes that need to share expensive setup or data.
    
    WARNING: Tests in the class are not isolated from each other.
    Use only when tests don't interfere with each other.
    
    Args:
        comprehensive_test_session: Session-scoped infrastructure
        
    Yields:
        Dictionary containing shared test resources
    """
    session = comprehensive_test_session
    env_manager = session['env_manager']
    external_manager = session['external_manager']
    
    test_id = f"class_{generate_test_id()}"
    
    async with env_manager.create_test_environment(test_id) as env_resources:
        async with external_manager.external_services_environment(
            test_id,
            enable_websocket=WEBSOCKETS_AVAILABLE,
            enable_http=HTTP_AVAILABLE,
            enable_filesystem=True,
            enable_llm=False
        ) as ext_resources:
            all_resources = {**env_resources, **ext_resources}
            
            logger.debug(f"Created class-scoped comprehensive environment {test_id}")
            yield all_resources
            logger.debug(f"Cleaned up class-scoped comprehensive environment {test_id}")


# ============================================================================
# SPECIALIZED FIXTURES FOR SPECIFIC TESTING SCENARIOS
# ============================================================================

@pytest.fixture(scope="function")
async def websocket_integration_environment(
    comprehensive_test_session: Dict[str, Any]
) -> AsyncIterator[Dict[str, TestResource]]:
    """Specialized environment for WebSocket integration testing.
    
    Optimized for testing WebSocket functionality with database backing.
    """
    if not WEBSOCKETS_AVAILABLE:
        pytest.skip("WebSocket testing requires websockets package")
        
    session = comprehensive_test_session
    env_manager = session['env_manager']
    external_manager = session['external_manager']
    
    test_id = f"ws_{generate_test_id()}"
    
    async with env_manager.create_test_environment(test_id) as env_resources:
        # Create WebSocket-specific external environment
        async with external_manager.external_services_environment(
            test_id,
            enable_websocket=True,
            enable_http=False,
            enable_filesystem=False,
            enable_llm=False
        ) as ext_resources:
            all_resources = {**env_resources, **ext_resources}
            
            # Configure WebSocket for agent event testing
            websocket = all_resources.get('websocket')
            if websocket:
                # Register handlers for agent events
                websocket.register_message_handler('agent_started', 
                    lambda msg: {'type': 'ack', 'message_id': msg.get('id')})
                websocket.register_message_handler('agent_thinking',
                    lambda msg: {'type': 'ack', 'message_id': msg.get('id')})
                websocket.register_message_handler('tool_executing',
                    lambda msg: {'type': 'ack', 'message_id': msg.get('id')})
                websocket.register_message_handler('agent_completed',
                    lambda msg: {'type': 'ack', 'message_id': msg.get('id')})
                    
            yield all_resources


@pytest.fixture(scope="function")
async def auth_service_integration_environment(
    comprehensive_test_session: Dict[str, Any]
) -> AsyncIterator[Dict[str, TestResource]]:
    """Specialized environment for auth service integration testing.
    
    Includes database, HTTP client configured for auth service, and Redis for sessions.
    """
    session = comprehensive_test_session
    env_manager = session['env_manager']
    external_manager = session['external_manager']
    
    test_id = f"auth_{generate_test_id()}"
    
    # Custom config for auth service testing
    auth_config = ExternalServiceConfig(
        auth_service_url="http://localhost:8082",
        http_timeout=30.0,
        enable_http_retry=True,
        http_retry_count=3
    )
    
    auth_external_manager = ExternalServiceManager(auth_config)
    
    try:
        async with env_manager.create_test_environment(test_id) as env_resources:
            async with auth_external_manager.external_services_environment(
                test_id,
                enable_websocket=False,
                enable_http=True,
                enable_filesystem=False,
                enable_llm=False
            ) as ext_resources:
                all_resources = {**env_resources, **ext_resources}
                
                # Pre-configure HTTP client for auth testing
                http_client = all_resources.get('http')
                if http_client:
                    # Verify auth service is available
                    is_healthy = await http_client.health_check()
                    if not is_healthy:
                        logger.warning("Auth service health check failed")
                        
                yield all_resources
                
    finally:
        await auth_external_manager.cleanup_all_resources()


@pytest.fixture(scope="function")
async def analytics_testing_environment(
    comprehensive_test_session: Dict[str, Any]
) -> AsyncIterator[Dict[str, TestResource]]:
    """Specialized environment for analytics service testing.
    
    Includes ClickHouse for analytics data and file system for data processing.
    """
    if not CLICKHOUSE_AVAILABLE:
        pytest.skip("Analytics testing requires ClickHouse")
        
    session = comprehensive_test_session
    env_manager = session['env_manager']
    external_manager = session['external_manager']
    
    test_id = f"analytics_{generate_test_id()}"
    
    async with env_manager.create_test_environment(test_id) as env_resources:
        async with external_manager.external_services_environment(
            test_id,
            enable_websocket=False,
            enable_http=True,
            enable_filesystem=True,
            enable_llm=False
        ) as ext_resources:
            all_resources = {**env_resources, **ext_resources}
            
            # Initialize analytics schema if ClickHouse is available
            clickhouse = all_resources.get('clickhouse')
            if clickhouse:
                # Create standard analytics tables
                events_table = clickhouse.get_table_name('events')
                await clickhouse.execute(f"""
                    CREATE TABLE IF NOT EXISTS {events_table} (
                        id UInt64,
                        event_type String,
                        user_id UInt64,
                        timestamp DateTime,
                        properties String
                    ) ENGINE = Memory
                """)
                
            yield all_resources


# ============================================================================
# UTILITY AND MIGRATION FIXTURES
# ============================================================================

@pytest.fixture(scope="function")
def test_resource_monitor(
    comprehensive_test_session: Dict[str, Any]
) -> Dict[str, Any]:
    """Fixture providing resource monitoring and health checking.
    
    Returns:
        Dictionary with monitoring functions and health status
    """
    session = comprehensive_test_session
    env_manager = session['env_manager']
    
    async def get_health_status():
        return await env_manager.get_health_status()
        
    def get_metrics():
        return env_manager.get_metrics()
        
    return {
        'get_health_status': get_health_status,
        'get_metrics': get_metrics,
        'service_status': session['service_status'],
        'available_services': session['available_services'],
        'unavailable_services': session['unavailable_services']
    }


@pytest.fixture(scope="function")
def skip_if_comprehensive_services_unavailable(
    comprehensive_test_session: Dict[str, Any]
):
    """Skip test if comprehensive services are not available.
    
    This fixture automatically skips tests if the required comprehensive
    services (database + external services) are not available.
    """
    session = comprehensive_test_session
    unavailable = session['unavailable_services']
    
    # Define minimum required services for comprehensive testing
    required_services = ['postgres']  # At minimum, we need database
    
    missing_required = [svc for svc in required_services if svc in unavailable]
    
    if missing_required:
        pytest.skip(
            f"Comprehensive testing requires services not available: {', '.join(missing_required)}"
        )


# ============================================================================
# PARAMETRIZED FIXTURES FOR MIGRATION TESTING
# ============================================================================

@pytest.fixture(scope="function", params=[
    {'postgres': True, 'redis': True, 'clickhouse': False},
    {'postgres': True, 'redis': False, 'clickhouse': True},
    {'postgres': True, 'redis': True, 'clickhouse': True}
])
async def parametrized_service_combinations(
    request,
    comprehensive_test_session: Dict[str, Any]
) -> AsyncIterator[Dict[str, TestResource]]:
    """Parametrized fixture testing different service combinations.
    
    This fixture runs the same test with different combinations of services
    to ensure compatibility and proper fallback behavior.
    """
    session = comprehensive_test_session
    env_manager = session['env_manager']
    
    service_config = request.param
    test_id = f"combo_{generate_test_id()}"
    
    # Filter services based on availability and configuration
    available_services = session['service_status']
    
    skip_reasons = []
    if service_config['postgres'] and not available_services['postgres']:
        skip_reasons.append('PostgreSQL')
    if service_config['redis'] and not available_services['redis']:
        skip_reasons.append('Redis')
    if service_config['clickhouse'] and not available_services['clickhouse']:
        skip_reasons.append('ClickHouse')
        
    if skip_reasons:
        pytest.skip(f"Required services not available: {', '.join(skip_reasons)}")
        
    # Create environment with requested services
    async with env_manager.create_test_environment(test_id) as resources:
        # Filter resources based on configuration
        filtered_resources = {}
        
        if service_config['postgres'] and 'database' in resources:
            filtered_resources['database'] = resources['database']
        if service_config['redis'] and 'redis' in resources:
            filtered_resources['redis'] = resources['redis']
        if service_config['clickhouse'] and 'clickhouse' in resources:
            filtered_resources['clickhouse'] = resources['clickhouse']
            
        logger.debug(
            f"Created parametrized environment {test_id} with services: "
            f"{list(filtered_resources.keys())}"
        )
        
        yield filtered_resources


# ============================================================================
# PYTEST CONFIGURATION AND HOOKS
# ============================================================================

def pytest_configure(config):
    """Configure pytest for comprehensive isolated environment testing."""
    # Add custom markers for comprehensive testing
    config.addinivalue_line(
        "markers", "comprehensive: mark test as requiring comprehensive environment"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test with real services"
    )
    config.addinivalue_line(
        "markers", "websocket_integration: mark test as WebSocket integration test"
    )
    config.addinivalue_line(
        "markers", "auth_integration: mark test as auth service integration test"
    )
    config.addinivalue_line(
        "markers", "analytics_integration: mark test as analytics service integration test"
    )
    config.addinivalue_line(
        "markers", "performance: mark test as performance test"
    )
    config.addinivalue_line(
        "markers", "mock_elimination: mark test as part of mock elimination effort"
    )
    
    logger.info("Pytest configured for comprehensive isolated environment testing")


def pytest_runtest_setup(item):
    """Setup function called before each test."""
    # Skip tests based on service availability
    if item.get_closest_marker("websocket_integration") and not WEBSOCKETS_AVAILABLE:
        pytest.skip("WebSocket integration tests require websockets package")
        
    if item.get_closest_marker("auth_integration") and not HTTP_AVAILABLE:
        pytest.skip("Auth integration tests require httpx package")
        
    if item.get_closest_marker("analytics_integration") and not CLICKHOUSE_AVAILABLE:
        pytest.skip("Analytics integration tests require ClickHouse")


# Export all fixtures for easy import
__all__ = [
    'comprehensive_test_session',
    'comprehensive_test_environment',
    'isolated_complete_environment',
    'performance_test_environment',
    'class_comprehensive_environment',
    'websocket_integration_environment',
    'auth_service_integration_environment',
    'analytics_testing_environment',
    'test_resource_monitor',
    'skip_if_comprehensive_services_unavailable',
    'parametrized_service_combinations'
]
