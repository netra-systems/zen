"""
Single Source of Truth (SSOT) Test Framework

This package provides the canonical test infrastructure that eliminates all duplicate
test implementations across the codebase. It includes:

1. SSotBaseTestCase - The ONE test base class all tests must inherit from
2. SSotMockFactory - The ONE mock factory for all mock creation
3. Comprehensive environment isolation and metrics tracking
4. Backwards compatibility for seamless migration

Usage:
    from test_framework.ssot import SSotBaseTestCase, create_mock_agent
    
    class MyTest(SSotBaseTestCase):
        def test_something(self):
            agent = create_mock_agent()
            # Test logic here

CRITICAL: This package replaces 6,096+ duplicate test implementations.
All new tests must use these SSOT classes.
"""

# Import all SSOT classes for easy access
from .base_test_case import (
    SSotBaseTestCase,
    SSotAsyncTestCase,
    SsotTestMetrics,
    SsotTestContext,
    # Backwards compatibility aliases
    BaseTestCase,
    AsyncTestCase,
    BaseTestMixin,
    TestErrorHandling,
    TestIntegration,
    TestIntegrationScenarios,
    TestErrorContext,
)

from .mock_factory import (
    SSotMockFactory,
    SSotMockAgent,
    SSotMockAgentService,
    SSotMockServiceManager,
    SSotMockDatabase,
    SSotMockRedis,
    MockConfiguration,
    AgentState,
    ServiceStatus,
    get_mock_factory,
    create_mock_agent,
    create_mock_agent_service,
    # Backwards compatibility aliases
    MockAgent,
    MockAgentService,
    MockServiceManager,
)

__all__ = [
    # Core SSOT Classes
    "SSotBaseTestCase",
    "SSotAsyncTestCase",
    "SsotTestMetrics",
    "SsotTestContext",
    "SSotMockFactory",
    "SSotMockAgent",
    "SSotMockAgentService",
    "SSotMockServiceManager", 
    "SSotMockDatabase",
    "SSotMockRedis",
    
    # Configuration and Enums
    "MockConfiguration",
    "AgentState",
    "ServiceStatus",
    
    # Convenience Functions
    "get_mock_factory",
    "create_mock_agent",
    "create_mock_agent_service",
    
    # Backwards Compatibility Aliases
    "BaseTestCase",
    "AsyncTestCase", 
    "BaseTestMixin",
    "TestErrorHandling",
    "TestIntegration",
    "TestIntegrationScenarios", 
    "TestErrorContext",
    "MockAgent",
    "MockAgentService",
    "MockServiceManager",
]

# Package metadata
__version__ = "1.0.0"
__author__ = "Netra Core Team"
__description__ = "Single Source of Truth Test Framework - Eliminates 6,096+ duplicate test implementations"