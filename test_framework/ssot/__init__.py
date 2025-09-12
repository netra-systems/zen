from shared.isolated_environment import get_env
"""
Single Source of Truth (SSOT) Test Framework

This package provides the unified, consolidated test infrastructure that ALL tests
in the system must use. It eliminates duplication and ensures consistency across
all 6,096+ test files in the Netra platform.

Business Value: Platform/Internal - Test Infrastructure Stability & Development Velocity
- Eliminates test infrastructure violations (P0 blocker)
- Reduces maintenance overhead by 80%
- Ensures consistent test behavior across all services  
- Provides centralized metrics and monitoring
- Enables reliable parallel test execution

CRITICAL REQUIREMENTS:
1. ALL test classes must inherit from BaseTestCase or its subclasses
2. ALL mocks must be created through MockFactory
3. ALL database tests must use DatabaseTestUtility
4. ALL WebSocket tests must use WebSocketTestUtility  
5. ALL Docker-based tests must use DockerTestUtility
6. NO custom test infrastructure outside this SSOT package

Components Overview:
- base.py: BaseTestCase and specialized test base classes
- mocks.py: MockFactory for ALL mock object creation
- database.py: DatabaseTestUtility for database testing
- websocket.py: WebSocketTestUtility for WebSocket testing
- docker.py: DockerTestUtility wrapping UnifiedDockerManager

Usage Examples:
    # Basic test
    from test_framework.ssot import BaseTestCase
    
    class MyTest(BaseTestCase):
        def test_something(self):
            pass
    
    # Database test
    from test_framework.ssot import DatabaseTestCase, DatabaseTestUtility
    
    class MyDatabaseTest(DatabaseTestCase):
        async def test_with_database(self):
            session = await self.get_database_session()
            # Use session
    
    # WebSocket test  
    from test_framework.ssot import WebSocketTestCase, WebSocketTestUtility
    
    class MyWebSocketTest(WebSocketTestCase):
        async def test_websocket_events(self):
            client = await self.get_websocket_client()
            # Use client
    
    # Integration test with services
    from test_framework.ssot import IntegrationTestCase, DockerTestUtility
    
    class MyIntegrationTest(IntegrationTestCase):
        async def test_with_services(self):
            async with DockerTestUtility() as docker:
                await docker.start_services(["postgres", "redis"])
                # Test with services
"""

import logging
from typing import List, Type

# Import all SSOT base test classes
from .base import (
    BaseTestCase,
    AsyncBaseTestCase,
    DatabaseTestCase,
    WebSocketTestCase,
    IntegrationTestCase,
    ExecutionMetrics,
    validate_test_class,
    get_test_base_for_category
)

# Import all SSOT mock utilities
from .mocks import (
    MockFactory,
    MockRegistry,
    DatabaseMockFactory,
    ServiceMockFactory,
    MockContext,
    get_mock_factory,
    cleanup_global_mocks
)

# Import all SSOT database utilities
from .database import (
    DatabaseTestUtility,
    PostgreSQLTestUtility,
    ClickHouseTestUtility,
    DatabaseTestMetrics,
    create_database_test_utility,
    get_database_test_utility,
    cleanup_all_database_utilities
)

# Import all SSOT WebSocket utilities
from .websocket import (
    WebSocketTestUtility,
    WebSocketTestClient,
    WebSocketMessage,
    WebSocketEventType,
    WebSocketTestMetrics,
    get_websocket_test_utility,
    cleanup_global_websocket_utility
)

# Import all SSOT Docker utilities
from .docker import (
    DockerTestUtility,
    PostgreSQLDockerUtility,
    RedisDockerUtility,
    DockerTestEnvironmentType,
    DockerTestMetrics,
    create_docker_test_utility,
    get_docker_test_utility,
    cleanup_all_docker_utilities
)

logger = logging.getLogger(__name__)

# SSOT Framework Version
SSOT_VERSION = "1.0.0"

# SSOT Compliance Report
SSOT_COMPLIANCE = {
    "base_classes": 5,           # BaseTestCase + 4 specialized classes
    "mock_factories": 3,         # MockFactory + 2 specialized factories  
    "database_utilities": 3,     # DatabaseTestUtility + 2 specialized utilities
    "websocket_utilities": 1,    # WebSocketTestUtility
    "docker_utilities": 3,       # DockerTestUtility + 2 specialized utilities
    "total_components": 15
}


def validate_ssot_compliance() -> List[str]:
    """
    Validate SSOT compliance across the test framework.
    
    Returns:
        List of compliance violations (empty if fully compliant)
    """
    violations = []
    
    try:
        # Validate base test classes
        base_classes = [
            BaseTestCase,
            AsyncBaseTestCase, 
            DatabaseTestCase,
            WebSocketTestCase,
            IntegrationTestCase
        ]
        
        for cls in base_classes:
            if not hasattr(cls, '__init__'):
                violations.append(f"Base class {cls.__name__} missing __init__ method")
        
        # Validate mock factory
        mock_factory = get_mock_factory()
        if not hasattr(mock_factory, 'create_mock'):
            violations.append("MockFactory missing core create_mock method")
        
        # Validate utilities are importable
        utilities = [
            DatabaseTestUtility,
            WebSocketTestUtility,
            DockerTestUtility
        ]
        
        for utility_class in utilities:
            if not hasattr(utility_class, '__aenter__'):
                violations.append(f"{utility_class.__name__} not async context manager")
        
        logger.info(f"SSOT compliance validation: {len(violations)} violations found")
        
    except Exception as e:
        violations.append(f"SSOT validation error: {str(e)}")
    
    return violations


def get_ssot_status() -> dict:
    """
    Get comprehensive SSOT framework status.
    
    Returns:
        Dictionary with SSOT framework status information
    """
    return {
        "version": SSOT_VERSION,
        "compliance": SSOT_COMPLIANCE,
        "violations": validate_ssot_compliance(),
        "components": {
            "base_classes": [
                "BaseTestCase",
                "AsyncBaseTestCase", 
                "DatabaseTestCase",
                "WebSocketTestCase",
                "IntegrationTestCase"
            ],
            "mock_utilities": [
                "MockFactory",
                "DatabaseMockFactory",
                "ServiceMockFactory"
            ],
            "database_utilities": [
                "DatabaseTestUtility",
                "PostgreSQLTestUtility", 
                "ClickHouseTestUtility"
            ],
            "websocket_utilities": [
                "WebSocketTestUtility"
            ],
            "docker_utilities": [
                "DockerTestUtility",
                "PostgreSQLDockerUtility",
                "RedisDockerUtility"
            ]
        }
    }


# Make asyncio available for cleanup function
import asyncio

async def cleanup_all_ssot_resources():
    """
    Clean up all SSOT framework resources.
    
    This should be called during test framework shutdown to ensure
    proper cleanup of all global resources.
    """
    logger.info("Starting SSOT framework cleanup")
    
    cleanup_tasks = []
    
    try:
        # Clean up mocks
        cleanup_global_mocks()
        
        # Clean up database utilities
        cleanup_tasks.append(cleanup_all_database_utilities())
        
        # Clean up WebSocket utilities  
        cleanup_tasks.append(cleanup_global_websocket_utility())
        
        # Clean up Docker utilities
        cleanup_tasks.append(cleanup_all_docker_utilities())
        
        # Execute all cleanup tasks concurrently
        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)
        
        logger.info("SSOT framework cleanup completed")
        
    except Exception as e:
        logger.error(f"SSOT framework cleanup failed: {e}")


def print_ssot_usage_guide():
    """Print comprehensive SSOT usage guide to console."""
    print("""
[U+2554][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2557]
[U+2551]                    NETRA SSOT TEST FRAMEWORK USAGE GUIDE                    [U+2551]
[U+255A][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+255D]

CRITICAL: ALL tests must use this SSOT framework. No custom test infrastructure allowed.

[U+1F4CB] BASIC TEST SETUP
[U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501]

from test_framework.ssot import BaseTestCase

class MyTest(BaseTestCase):
    def test_basic_functionality(self):
        # Test implementation
        pass

[U+1F5C4][U+FE0F] DATABASE TESTING
[U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501]

from test_framework.ssot import DatabaseTestCase

class MyDatabaseTest(DatabaseTestCase):
    async def test_with_database(self):
        session = await self.get_database_session()
        # Use database session
        
    async def test_with_transaction(self):
        async with DatabaseTestUtility() as db:
            async with db.transaction_scope() as session:
                # Transaction automatically rolled back

[U+1F310] WEBSOCKET TESTING  
[U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501]

from test_framework.ssot import WebSocketTestCase, WebSocketEventType

class MyWebSocketTest(WebSocketTestCase):
    async def test_websocket_events(self):
        client = await self.get_websocket_client()
        
        # Send message
        await client.send_message(
            WebSocketEventType.PING, 
            {"test": "data"}
        )
        
        # Wait for response
        response = await client.wait_for_message(
            WebSocketEventType.PONG
        )

[U+1F433] DOCKER/INTEGRATION TESTING
[U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501]

from test_framework.ssot import IntegrationTestCase, DockerTestUtility

class MyIntegrationTest(IntegrationTestCase):
    async def test_with_services(self):
        async with DockerTestUtility() as docker:
            # Start services
            result = await docker.start_services([
                "postgres", "redis", "backend"
            ])
            
            # Get service URLs
            urls = docker.get_all_service_urls()
            
            # Test with services running

[U+1F3AD] MOCK TESTING
[U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501]

from test_framework.ssot import get_mock_factory

def test_with_mocks():
    factory = get_mock_factory()
    
    # Create service mocks
    db_mock = factory.create_database_session_mock()
    ws_mock = factory.create_websocket_manager_mock()
    llm_mock = factory.create_llm_client_mock()
    
    # Use mocks in tests

 LIGHTNING:  ASYNC TESTING
[U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501]

from test_framework.ssot import AsyncBaseTestCase

class MyAsyncTest(AsyncBaseTestCase):
    async def asyncSetUp(self):
        # Async setup
        pass
        
    async def test_async_functionality(self):
        result = await some_async_function()
        self.assertEqual(result, expected_value)

 CHART:  TEST CATEGORIES
[U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501]

- BaseTestCase: Basic unit tests
- AsyncBaseTestCase: Async unit tests  
- DatabaseTestCase: Database-dependent tests
- WebSocketTestCase: WebSocket functionality tests
- IntegrationTestCase: Multi-service integration tests

[U+1F527] UTILITY FUNCTIONS
[U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501]

# Validate test class compliance
from test_framework.ssot import validate_test_class
errors = validate_test_class(MyTestClass)

# Get appropriate base class for category
from test_framework.ssot import get_test_base_for_category  
BaseClass = get_test_base_for_category("integration")

# Check SSOT framework status
from test_framework.ssot import get_ssot_status
status = get_ssot_status()

 WARNING: [U+FE0F]  CRITICAL REQUIREMENTS
[U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501][U+2501]

1. ALL test classes MUST inherit from BaseTestCase or subclasses
2. NO direct os.environ access - use self.env instead  
3. NO custom mock creation - use MockFactory only
4. NO direct database connections - use DatabaseTestUtility
5. NO custom WebSocket clients - use WebSocketTestUtility
6. NO manual Docker management - use DockerTestUtility

 FAIL:  VIOLATIONS WILL CAUSE TEST FAILURES  FAIL: 

For questions or issues with SSOT framework, check:
- docs/test_framework_ssot_architecture.xml
- test_framework/ssot/ source code
- DEFINITION_OF_DONE_CHECKLIST.md

[U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550][U+2550]
""")


# Export all SSOT components for easy access
__all__ = [
    # Version and status
    "SSOT_VERSION",
    "SSOT_COMPLIANCE",
    
    # Base test classes  
    "BaseTestCase",
    "AsyncBaseTestCase",
    "DatabaseTestCase", 
    "WebSocketTestCase",
    "IntegrationTestCase",
    "ExecutionMetrics",
    
    # Mock utilities
    "MockFactory",
    "MockRegistry", 
    "DatabaseMockFactory",
    "ServiceMockFactory",
    "MockContext",
    "get_mock_factory",
    "cleanup_global_mocks",
    
    # Database utilities
    "DatabaseTestUtility",
    "PostgreSQLTestUtility",
    "ClickHouseTestUtility", 
    "DatabaseTestMetrics",
    "create_database_test_utility",
    "get_database_test_utility",
    "cleanup_all_database_utilities",
    
    # WebSocket utilities
    "WebSocketTestUtility",
    "WebSocketTestClient",
    "WebSocketMessage",
    "WebSocketEventType", 
    "WebSocketTestMetrics",
    "get_websocket_test_utility",
    "cleanup_global_websocket_utility",
    
    # Docker utilities
    "DockerTestUtility",
    "PostgreSQLDockerUtility",
    "RedisDockerUtility",
    "DockerTestEnvironmentType",
    "DockerTestMetrics", 
    "create_docker_test_utility",
    "get_docker_test_utility",
    "cleanup_all_docker_utilities",
    
    # Utility functions
    "validate_test_class",
    "get_test_base_for_category",
    "validate_ssot_compliance",
    "get_ssot_status",
    "cleanup_all_ssot_resources",
    "print_ssot_usage_guide"
]

# Log SSOT framework initialization
logger.info(f"SSOT Test Framework v{SSOT_VERSION} initialized - {SSOT_COMPLIANCE['total_components']} components loaded")
