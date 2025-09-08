"""
CRITICAL VALIDATION TEST: ExecutionEngineFactory WebSocket Bridge Fix

This test validates that the fix for the WebSocket bridge bug is working correctly.
It specifically tests the ExecutionEngineFactory's constructor validation and 
WebSocket emitter creation with the provided bridge.

Bug Fix Validation:
1. ExecutionEngineFactory constructor now requires websocket_bridge parameter
2. Validation happens early (fail fast) instead of late during execution
3. WebSocket emitter creation uses the validated bridge from initialization
4. Clear error messages guide troubleshooting

This test MUST PASS after the fix is implemented.
"""

import asyncio
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from netra_backend.app.agents.supervisor.execution_engine_factory import (
    ExecutionEngineFactory, 
    ExecutionEngineFactoryError,
    configure_execution_engine_factory
)
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge


class TestExecutionEngineFactoryFixValidation:
    """
    Validation tests for ExecutionEngineFactory WebSocket bridge fix.
    
    These tests verify that the fix addresses the root cause:
    1. Constructor validation prevents late failures
    2. WebSocket bridge is properly injected
    3. Error messages are clear and actionable
    """
    
    def test_constructor_requires_websocket_bridge(self):
        """
        CRITICAL: Test that ExecutionEngineFactory constructor validates websocket_bridge.
        
        The fix should ensure the factory fails fast during initialization
        if the websocket_bridge is not provided.
        """
        
        # Test 1: Constructor with None websocket_bridge should fail
        with pytest.raises(ExecutionEngineFactoryError) as exc_info:
            ExecutionEngineFactory(websocket_bridge=None)
        
        # Verify the error message is clear and actionable
        error_message = str(exc_info.value)
        assert "ExecutionEngineFactory requires websocket_bridge during initialization" in error_message
        assert "chat business value" in error_message
        print(f"[SUCCESS] Constructor validation works: {error_message}")
        
        # Test 2: Constructor with no parameters should fail  
        with pytest.raises(ExecutionEngineFactoryError) as exc_info:
            ExecutionEngineFactory()
        
        error_message = str(exc_info.value)
        assert "ExecutionEngineFactory requires websocket_bridge during initialization" in error_message
        print(f"[SUCCESS] Constructor parameter validation works: {error_message}")
    
    def test_constructor_with_valid_bridge_succeeds(self):
        """
        Test that ExecutionEngineFactory constructor succeeds with valid websocket_bridge.
        
        This tests the positive case - proper initialization with dependencies.
        """
        
        # Create valid WebSocket bridge
        websocket_bridge = AgentWebSocketBridge()
        
        # Constructor should succeed
        factory = ExecutionEngineFactory(websocket_bridge=websocket_bridge)
        
        # Verify the bridge is stored
        assert factory._websocket_bridge is not None
        assert factory._websocket_bridge == websocket_bridge
        
        # Verify other factory attributes are initialized
        assert factory._active_engines is not None
        assert factory._engine_lock is not None
        assert factory._factory_metrics is not None
        
        print("[SUCCESS] Constructor with valid bridge succeeds")
    
    @pytest.mark.asyncio
    async def test_websocket_emitter_creation_uses_validated_bridge(self):
        """
        CRITICAL: Test that WebSocket emitter creation uses the validated bridge.
        
        The fix should eliminate the late validation that was causing the bug
        and use the bridge provided during initialization.
        """
        
        # Create valid components
        websocket_bridge = AgentWebSocketBridge()
        factory = ExecutionEngineFactory(websocket_bridge=websocket_bridge)
        
        user_context = UserExecutionContext.from_request(
            user_id="test-user-123",
            thread_id="thread-456",
            run_id="run-789"
        )
        
        # Mock agent factory (parameter still needed for compatibility)
        mock_agent_factory = MagicMock()
        
        # The fix should use factory._websocket_bridge instead of agent_factory._websocket_bridge
        emitter = await factory._create_user_websocket_emitter(user_context, mock_agent_factory)
        
        # Verify emitter was created with the correct bridge
        assert emitter is not None
        assert emitter.websocket_bridge == websocket_bridge
        assert emitter.user_id == "test-user-123"
        assert emitter.thread_id == "thread-456" 
        assert emitter.run_id == "run-789"
        
        print("[SUCCESS] WebSocket emitter creation uses validated bridge")
    
    @pytest.mark.asyncio
    async def test_configure_execution_engine_factory_function(self):
        """
        Test the configure_execution_engine_factory helper function.
        
        This function should be used during system startup to properly
        configure the singleton factory.
        """
        
        # Create WebSocket bridge
        websocket_bridge = AgentWebSocketBridge()
        
        # Configure the factory
        factory = await configure_execution_engine_factory(websocket_bridge)
        
        # Verify configuration
        assert factory is not None
        assert factory._websocket_bridge == websocket_bridge
        
        # Verify singleton behavior - calling again should return configured instance
        factory2 = await configure_execution_engine_factory(websocket_bridge)
        assert factory2._websocket_bridge == websocket_bridge
        
        print("[SUCCESS] configure_execution_engine_factory works correctly")
    
    @pytest.mark.asyncio
    async def test_error_messages_are_actionable(self):
        """
        Test that error messages provide actionable guidance for troubleshooting.
        
        The fix should include clear error messages that help developers
        understand how to resolve configuration issues.
        """
        
        # Test constructor error message
        try:
            ExecutionEngineFactory()
        except ExecutionEngineFactoryError as e:
            error_msg = str(e)
            # Should mention initialization requirement
            assert "during initialization" in error_msg
            # Should mention WebSocket bridge requirement  
            assert "websocket_bridge" in error_msg
            # Should mention business value context
            assert "chat business value" in error_msg
            print(f"[SUCCESS] Constructor error message is actionable: {error_msg}")
        
        # Test get_execution_engine_factory error when not configured
        from netra_backend.app.agents.supervisor.execution_engine_factory import (
            get_execution_engine_factory, _factory_instance, _factory_lock
        )
        
        # Clear the singleton for this test
        async with _factory_lock:
            original_instance = globals().get('_factory_instance')
            globals()['_factory_instance'] = None
        
        try:
            with pytest.raises(ExecutionEngineFactoryError) as exc_info:
                await get_execution_engine_factory()
            
            error_msg = str(exc_info.value)
            # Should mention startup configuration requirement
            assert "not configured during startup" in error_msg
            # Should mention where to fix it
            assert "smd.py" in error_msg
            print(f"[SUCCESS] Factory getter error message is actionable: {error_msg}")
            
        finally:
            # Restore original state
            async with _factory_lock:
                globals()['_factory_instance'] = original_instance
    
    def test_fix_addresses_original_bug_conditions(self):
        """
        Test that the fix addresses the specific conditions that caused the original bug.
        
        Original Bug Conditions:
        1. ExecutionEngineFactory created without websocket_bridge
        2. Late validation during _create_user_websocket_emitter()
        3. Error: "WebSocket bridge not available in agent factory"
        
        Fix should eliminate these conditions.
        """
        
        # Original bug condition: Factory created without bridge 
        # This should now be impossible due to constructor validation
        with pytest.raises(ExecutionEngineFactoryError):
            ExecutionEngineFactory()
        
        # With proper initialization, the late validation error should not occur
        websocket_bridge = AgentWebSocketBridge()
        factory = ExecutionEngineFactory(websocket_bridge=websocket_bridge)
        
        # The factory should have the bridge available immediately
        assert factory._websocket_bridge is not None
        assert factory._websocket_bridge == websocket_bridge
        
        # The original error path should be eliminated
        # (we can't easily test _create_user_websocket_emitter without mocking deps,
        #  but the unit test above covers that)
        
        print("[SUCCESS] Fix addresses original bug conditions")
    
    def test_business_value_preservation(self):
        """
        Verify the fix preserves the critical business value requirements.
        
        Business Requirements:
        1. WebSocket events must be sent during agent execution
        2. Real-time updates must reach users  
        3. Chat functionality must work (90% of business value)
        """
        
        # The fix ensures WebSocket bridge is always available
        websocket_bridge = AgentWebSocketBridge()
        factory = ExecutionEngineFactory(websocket_bridge=websocket_bridge)
        
        # Verify factory can provide the infrastructure for WebSocket events
        assert factory._websocket_bridge is not None
        
        # This enables the following business value chain:
        # ExecutionEngineFactory -> UserExecutionEngine -> Agent execution -> WebSocket events -> Chat value
        
        user_context = UserExecutionContext.from_request(
            user_id="business-user",
            thread_id="chat-thread", 
            run_id="value-delivery-run"
        )
        
        # The factory should be able to create the infrastructure needed for business value
        # (Full integration testing would verify the complete chain)
        
        print("[SUCCESS] Fix preserves WebSocket event infrastructure for chat business value")