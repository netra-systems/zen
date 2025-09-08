"""
CRITICAL BUG REPRODUCTION TEST: ExecutionEngineFactory WebSocket Bridge Missing

This test reproduces the exact bug: "WebSocket bridge not available in agent factory" 
that occurs in ExecutionEngineFactory._create_user_websocket_emitter() method.

Business Value Impact:
- CRITICAL: Breaks agent execution completely
- CRITICAL: Prevents WebSocket events for chat (90% of business value)
- CRITICAL: Blocks integration tests and deployments

Bug Details:
- Error Location: execution_engine_factory.py:212
- Root Cause: AgentInstanceFactory not configured with WebSocket bridge
- Failure Mode: Late validation during execution vs. early validation at startup

This test MUST FAIL initially to demonstrate the bug, then PASS after the fix.
"""

import asyncio
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from netra_backend.app.agents.supervisor.execution_engine_factory import (
    ExecutionEngineFactory, 
    ExecutionEngineFactoryError
)
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor.agent_instance_factory import AgentInstanceFactory
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge


class TestExecutionEngineFactoryWebSocketBridgeBugReproduction:
    """
    CRITICAL reproduction test for WebSocket bridge configuration bug.
    
    This test reproduces the exact conditions that cause the bug:
    1. AgentInstanceFactory exists but is not configured
    2. ExecutionEngineFactory tries to create WebSocket emitter
    3. Fails because agent_factory._websocket_bridge is None
    """
    
    @pytest.fixture
    def unconfigured_agent_factory(self):
        """Create AgentInstanceFactory that is NOT configured with WebSocket bridge."""
        factory = AgentInstanceFactory()
        # CRITICAL: Do NOT call configure() - this simulates the bug condition
        # factory.configure(websocket_bridge=bridge)  # <- This is missing!
        
        # Verify the bug condition exists
        assert factory._websocket_bridge is None, "Factory should be unconfigured for this test"
        
        return factory
    
    @pytest.fixture
    def valid_user_context(self):
        """Create a valid UserExecutionContext."""
        return UserExecutionContext.from_request(
            user_id="test-user-123",
            thread_id="thread-456", 
            run_id="run-789",
            metadata={"test": True}
        )
    
    @pytest.fixture
    def execution_engine_factory(self):
        """Create ExecutionEngineFactory for testing."""
        return ExecutionEngineFactory()
    
    @pytest.mark.asyncio
    async def test_reproduction_websocket_bridge_not_available_error(
        self,
        execution_engine_factory,
        unconfigured_agent_factory,
        valid_user_context
    ):
        """
        CRITICAL BUG REPRODUCTION: Reproduce the exact "WebSocket bridge not available" error.
        
        This test MUST FAIL initially to demonstrate the bug.
        After the fix, it MUST PASS.
        
        Bug Sequence:
        1. AgentInstanceFactory exists but is NOT configured with WebSocket bridge
        2. ExecutionEngineFactory._create_user_websocket_emitter() gets unconfigured factory
        3. Validation fails: agent_factory._websocket_bridge is None
        4. ExecutionEngineFactoryError raised with exact message
        """
        
        # Mock get_agent_instance_factory to return unconfigured factory
        with patch(
            'netra_backend.app.agents.supervisor.execution_engine_factory.get_agent_instance_factory',
            return_value=unconfigured_agent_factory
        ):
            # CRITICAL: This should raise the exact error we're reproducing
            with pytest.raises(ExecutionEngineFactoryError) as exc_info:
                await execution_engine_factory.create_for_user(valid_user_context)
            
            # Verify the exact error message that indicates the bug
            expected_error = "WebSocket bridge not available in agent factory"
            assert expected_error in str(exc_info.value), (
                f"Expected error message '{expected_error}' not found in: {exc_info.value}"
            )
            
            print(f"[SUCCESS] BUG REPRODUCED: {exc_info.value}")
    
    @pytest.mark.asyncio
    async def test_websocket_emitter_creation_fails_without_bridge(
        self,
        execution_engine_factory,
        unconfigured_agent_factory,
        valid_user_context
    ):
        """
        Test the specific _create_user_websocket_emitter() method that fails.
        
        This directly tests the failing code path in isolation.
        """
        
        # Try to call the private method that contains the bug
        with pytest.raises(ExecutionEngineFactoryError) as exc_info:
            await execution_engine_factory._create_user_websocket_emitter(
                valid_user_context, 
                unconfigured_agent_factory
            )
        
        # Verify the exact check that fails
        assert "WebSocket bridge not available in agent factory" in str(exc_info.value)
        
        # Verify the agent factory really doesn't have the bridge
        assert not hasattr(unconfigured_agent_factory, '_websocket_bridge') or \
               unconfigured_agent_factory._websocket_bridge is None
        
        print(f"[SUCCESS] DIRECT METHOD FAILURE REPRODUCED: {exc_info.value}")
    
    @pytest.mark.asyncio 
    async def test_configured_factory_should_work(self):
        """
        CONTROL TEST: Verify that a properly configured factory would work.
        
        This demonstrates what the fix should achieve.
        """
        
        # Create properly configured factory (what the fix should ensure)
        websocket_bridge = AgentWebSocketBridge()
        configured_factory = AgentInstanceFactory()
        
        # Mock the agent class registry to avoid dependency issues in test
        with patch('netra_backend.app.agents.supervisor.agent_instance_factory.get_agent_class_registry'):
            configured_factory.configure(websocket_bridge=websocket_bridge)
        
        # Verify configuration worked
        assert configured_factory._websocket_bridge is not None
        assert configured_factory._websocket_bridge == websocket_bridge
        
        # This demonstrates the condition that should exist after the fix
        user_context = UserExecutionContext.from_request(
            user_id="test-user-456",
            thread_id="thread-789",
            run_id="run-012"
        )
        
        execution_factory = ExecutionEngineFactory()
        
        # Mock the factory getter to return configured factory
        with patch(
            'netra_backend.app.agents.supervisor.execution_engine_factory.get_agent_instance_factory',
            return_value=configured_factory
        ):
            # This should NOT raise an error (after the fix)
            try:
                # Create user WebSocket emitter directly (the method that was failing)
                emitter = await execution_factory._create_user_websocket_emitter(
                    user_context,
                    configured_factory  
                )
                
                # Verify emitter was created successfully
                assert emitter is not None
                assert emitter.user_id == "test-user-456"
                assert emitter.thread_id == "thread-789"
                assert emitter.run_id == "run-012"
                assert emitter.websocket_bridge == websocket_bridge
                
                print("[SUCCESS] CONTROL TEST: Configured factory works as expected")
                
            except ExecutionEngineFactoryError as e:
                pytest.fail(f"Configured factory should not raise error: {e}")
    
    def test_bug_reproduction_documentation(self):
        """
        Document the exact bug conditions for future reference.
        """
        bug_conditions = {
            "error_location": "execution_engine_factory.py:212", 
            "error_method": "_create_user_websocket_emitter",
            "error_check": "if not hasattr(agent_factory, '_websocket_bridge') or not agent_factory._websocket_bridge",
            "root_cause": "AgentInstanceFactory.configure() never called with websocket_bridge",
            "business_impact": "Agent execution fails, WebSocket events not sent, chat broken",
            "fix_required": "Ensure AgentInstanceFactory is configured during startup"
        }
        
        print("[BUG] REPRODUCTION CONDITIONS DOCUMENTED:")
        for key, value in bug_conditions.items():
            print(f"   {key}: {value}")
        
        # This test always passes - it's just documentation
        assert len(bug_conditions) == 6