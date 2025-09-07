"""CRITICAL TEST FIXTURE: ExecutionEngineFactory Initialization for Tests

Business Value Justification:
- Segment: Platform/Internal  
- Business Goal: Test Infrastructure Stability
- Value Impact: Enables agent integration testing - critical for $500K+ ARR platform
- Strategic Impact: Prevents ExecutionEngineFactoryError during test execution

PROBLEM SOLVED:
Integration tests fail with "ExecutionEngineFactory not configured during startup"
because tests run independently without the full app startup sequence that normally
configures the factory singleton.

SOLUTION:
Test fixtures that initialize ExecutionEngineFactory with proper WebSocket bridge
before tests run, following the same pattern as app startup but for test environment.

CRITICAL REQUIREMENTS per CLAUDE.md:
1. REAL SERVICES OVER MOCKS - Use real WebSocket bridge, not mocks
2. SSOT COMPLIANCE - Follow existing factory configuration patterns  
3. NO STARTUP DEPENDENCY - Tests work without full app startup
4. BUSINESS VALUE FOCUS - Enable agent execution validation for platform stability
"""

import asyncio
import pytest
from typing import Optional, AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

# SSOT imports following CLAUDE.md absolute import requirements
from netra_backend.app.agents.supervisor.execution_engine_factory import (
    ExecutionEngineFactory,
    configure_execution_engine_factory,
    get_execution_engine_factory,
    _factory_instance,
    _factory_lock
)
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.agents.supervisor.agent_instance_factory import configure_agent_instance_factory
from test_framework.ssot.base_test_case import logger


class ExecutionEngineFactoryTestManager:
    """Manages ExecutionEngineFactory initialization for test environments.
    
    This manager handles the complete initialization sequence needed for 
    ExecutionEngineFactory to work in tests, including WebSocket bridge 
    setup and singleton configuration.
    """
    
    def __init__(self):
        self.factory_instance: Optional[ExecutionEngineFactory] = None
        self.websocket_bridge: Optional[AgentWebSocketBridge] = None
        self.cleanup_tasks = []
        
    async def initialize_for_tests(self) -> ExecutionEngineFactory:
        """Initialize ExecutionEngineFactory with all dependencies for test environment.
        
        This follows the same initialization pattern as smd.py startup but
        adapted for test environment without full app startup.
        
        Returns:
            ExecutionEngineFactory: Configured factory instance
            
        Raises:
            RuntimeError: If initialization fails
        """
        try:
            # Step 1: Create AgentWebSocketBridge (required by factory)
            logger.info("Creating AgentWebSocketBridge for test environment...")
            self.websocket_bridge = AgentWebSocketBridge()
            
            if not self.websocket_bridge:
                raise RuntimeError("Failed to create AgentWebSocketBridge for tests")
                
            logger.info("✓ AgentWebSocketBridge created for tests")
            
            # Step 2: Configure ExecutionEngineFactory singleton
            logger.info("Configuring ExecutionEngineFactory singleton for tests...")
            self.factory_instance = await configure_execution_engine_factory(
                websocket_bridge=self.websocket_bridge
            )
            
            if not self.factory_instance:
                raise RuntimeError("Failed to configure ExecutionEngineFactory")
                
            logger.info("✓ ExecutionEngineFactory configured with WebSocket bridge")
            
            # Step 3: Configure AgentInstanceFactory (may be needed by some tests)
            try:
                await configure_agent_instance_factory(
                    websocket_bridge=self.websocket_bridge,
                    websocket_manager=None,  # Will be created per-request
                    llm_manager=None,  # Tests can provide their own
                    tool_dispatcher=None  # Will be created per-request
                )
                logger.info("✓ AgentInstanceFactory configured for tests")
            except Exception as e:
                # Non-critical for basic factory functionality
                logger.warning(f"AgentInstanceFactory configuration skipped: {e}")
            
            # Step 4: Verify factory functionality
            await self._verify_factory_functionality()
            
            logger.info("✅ ExecutionEngineFactory fully initialized for tests")
            return self.factory_instance
            
        except Exception as e:
            logger.error(f"❌ ExecutionEngineFactory test initialization failed: {e}")
            await self.cleanup()
            raise RuntimeError(f"ExecutionEngineFactory initialization failed: {e}") from e
    
    async def _verify_factory_functionality(self):
        """Verify that the factory is properly configured and functional."""
        if not self.factory_instance:
            raise RuntimeError("Factory instance not available for verification")
            
        # Test factory metrics access
        metrics = self.factory_instance.get_factory_metrics()
        if not isinstance(metrics, dict):
            raise RuntimeError("Factory metrics not accessible")
            
        # Test WebSocket bridge availability
        if not hasattr(self.factory_instance, '_websocket_bridge'):
            raise RuntimeError("Factory does not have WebSocket bridge configured")
            
        if self.factory_instance._websocket_bridge is None:
            raise RuntimeError("Factory WebSocket bridge is None")
            
        logger.info("✓ Factory functionality verified")
    
    async def cleanup(self):
        """Clean up test factory resources."""
        try:
            # Cleanup factory if it exists
            if self.factory_instance:
                try:
                    await self.factory_instance.shutdown()
                    logger.info("✓ ExecutionEngineFactory shutdown complete")
                except Exception as e:
                    logger.warning(f"Factory shutdown error: {e}")
                    
            # Reset singleton state for next test
            global _factory_instance
            async with _factory_lock:
                _factory_instance = None
                
            logger.info("✓ Factory singleton state reset")
            
            # Run any additional cleanup tasks
            for task in self.cleanup_tasks:
                try:
                    await task()
                except Exception as e:
                    logger.warning(f"Cleanup task error: {e}")
                    
            self.cleanup_tasks.clear()
            self.factory_instance = None
            self.websocket_bridge = None
            
        except Exception as e:
            logger.error(f"❌ Factory cleanup error: {e}")


# Global test manager instance
_test_manager: Optional[ExecutionEngineFactoryTestManager] = None


@pytest.fixture(scope="function")
async def execution_engine_factory_test_initialized() -> AsyncGenerator[ExecutionEngineFactory, None]:
    """Pytest fixture that provides initialized ExecutionEngineFactory for tests.
    
    This fixture handles the complete initialization and cleanup sequence,
    ensuring each test gets a properly configured factory.
    
    Usage in test:
        async def test_agent_execution(execution_engine_factory_test_initialized):
            factory = execution_engine_factory_test_initialized
            # Factory is ready to use - no more "not configured" errors
            engine = await factory.create_for_user(user_context)
    """
    global _test_manager
    
    # Initialize factory for this test
    _test_manager = ExecutionEngineFactoryTestManager()
    
    try:
        factory = await _test_manager.initialize_for_tests()
        logger.info("🔧 ExecutionEngineFactory test fixture ready")
        yield factory
        
    finally:
        # Cleanup after test
        if _test_manager:
            await _test_manager.cleanup()
            _test_manager = None
            logger.info("🧹 ExecutionEngineFactory test fixture cleaned up")


@pytest.fixture(scope="session")
async def execution_engine_factory_session() -> AsyncGenerator[ExecutionEngineFactory, None]:
    """Session-scoped fixture for ExecutionEngineFactory (shared across multiple tests).
    
    Use this when you need the factory to persist across multiple tests in a session
    for performance reasons. Be aware that this shares state between tests.
    
    Usage:
        async def test_multiple_agents(execution_engine_factory_session):
            factory = execution_engine_factory_session
            # Same factory instance used across all tests in session
    """
    global _test_manager
    
    # Initialize factory once for entire session
    _test_manager = ExecutionEngineFactoryTestManager()
    
    try:
        factory = await _test_manager.initialize_for_tests()
        logger.info("🏭 ExecutionEngineFactory session fixture ready")
        yield factory
        
    finally:
        # Cleanup at end of session
        if _test_manager:
            await _test_manager.cleanup()
            _test_manager = None
            logger.info("🏭 ExecutionEngineFactory session fixture cleaned up")


async def configure_execution_engine_factory_for_test() -> ExecutionEngineFactory:
    """Direct function to configure ExecutionEngineFactory for test use.
    
    Use this in test setup when you need manual control over factory initialization
    rather than using pytest fixtures.
    
    Returns:
        ExecutionEngineFactory: Configured factory ready for test use
        
    Example:
        async def test_setup():
            factory = await configure_execution_engine_factory_for_test()
            # Factory ready to use
            return factory
    """
    manager = ExecutionEngineFactoryTestManager()
    return await manager.initialize_for_tests()


def get_or_create_websocket_bridge_for_tests() -> AgentWebSocketBridge:
    """Get or create WebSocket bridge for test use.
    
    Provides a real WebSocket bridge instance that can be used in tests
    that need to initialize ExecutionEngineFactory manually.
    
    Returns:
        AgentWebSocketBridge: Real bridge instance for tests
    """
    global _test_manager
    
    if _test_manager and _test_manager.websocket_bridge:
        return _test_manager.websocket_bridge
    
    # Create new bridge for standalone use
    return AgentWebSocketBridge()


# Backward compatibility fixtures
@pytest.fixture(scope="function")
async def execution_engine_factory(execution_engine_factory_test_initialized):
    """Backward compatibility fixture - same as execution_engine_factory_test_initialized."""
    return execution_engine_factory_test_initialized


@pytest.fixture(scope="function") 
async def websocket_bridge_for_tests():
    """Fixture providing WebSocket bridge for tests that need it separately."""
    bridge = get_or_create_websocket_bridge_for_tests()
    yield bridge
    # No cleanup needed - handled by factory fixtures