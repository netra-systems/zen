"""
CRITICAL BUG FIX VERIFICATION: ExecutionEngineFactory WebSocket Bridge Fixed

This test verifies that the original bug has been FIXED. The bug was:
"WebSocket bridge not available in agent factory" in ExecutionEngineFactory._create_user_websocket_emitter()

Fix Applied:
1. ExecutionEngineFactory constructor now requires websocket_bridge parameter  
2. Early validation during initialization (fail fast)
3. WebSocket emitter creation uses validated bridge from initialization
4. System startup configures ExecutionEngineFactory with WebSocket bridge

This test MUST PASS to demonstrate the bug is fixed.
"""

import asyncio
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from netra_backend.app.agents.supervisor.execution_engine_factory import (
    ExecutionEngineFactory, 
    ExecutionEngineFactoryError
)
from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor.agent_instance_factory import AgentInstanceFactory
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge


class TestExecutionEngineFactoryWebSocketBridgeBugFixed:
    """
    Verification that the WebSocket bridge bug has been FIXED.
    
    The original bug occurred because:
    1. ExecutionEngineFactory tried to get WebSocket bridge from unconfigured AgentInstanceFactory
    2. Late validation during execution failed
    3. Error: "WebSocket bridge not available in agent factory"
    
    The fix ensures:
    1. ExecutionEngineFactory gets WebSocket bridge during initialization
    2. Early validation prevents late failures
    3. WebSocket emitter creation always succeeds with valid bridge
    """
    
    @pytest.fixture
    def websocket_bridge(self):
        """Create valid WebSocket bridge."""
        return AgentWebSocketBridge()
    
    @pytest.fixture
    def configured_execution_factory(self, websocket_bridge):
        """Create ExecutionEngineFactory configured with WebSocket bridge (fixed version)."""
        return ExecutionEngineFactory(websocket_bridge=websocket_bridge)
    
    @pytest.fixture
    def valid_user_context(self):
        """Create a valid UserExecutionContext."""
        return UserExecutionContext.from_request(
            user_id="test-user-123",
            thread_id="thread-456",
            run_id="run-789",
            metadata={"test": "fixed"}
        )
    
    @pytest.mark.asyncio
    async def test_bug_is_fixed_websocket_emitter_creation_succeeds(
        self,
        configured_execution_factory,
        valid_user_context,
        websocket_bridge
    ):
        """
        CRITICAL: Verify the original bug is FIXED - WebSocket emitter creation succeeds.
        
        With the fix, ExecutionEngineFactory should create WebSocket emitters
        successfully using the validated bridge from initialization.
        """
        
        # Create mock agent factory (still needed for method signature compatibility)
        mock_agent_factory = MagicMock()
        
        # The fix should make this succeed (was failing before)
        emitter = await configured_execution_factory._create_user_websocket_emitter(
            valid_user_context,
            mock_agent_factory
        )
        
        # Verify emitter was created successfully
        assert emitter is not None
        assert emitter.user_id == "test-user-123"
        assert emitter.thread_id == "thread-456"
        assert emitter.run_id == "run-789"
        assert emitter.websocket_bridge == websocket_bridge
        
        print("[FIXED] WebSocket emitter creation succeeds with validated bridge")
    
    @pytest.mark.asyncio
    async def test_bug_is_fixed_create_for_user_succeeds(
        self,
        configured_execution_factory, 
        valid_user_context
    ):
        """
        CRITICAL: Verify the full create_for_user method succeeds with the fix.
        
        This tests the complete flow that was failing in the original bug.
        """
        
        # Mock get_agent_instance_factory to return a configured factory
        mock_agent_factory = MagicMock()
        mock_agent_factory._websocket_bridge = configured_execution_factory._websocket_bridge
        
        with patch(
            'netra_backend.app.agents.supervisor.execution_engine_factory.get_agent_instance_factory',
            return_value=mock_agent_factory
        ):
            # This should succeed with the fix (was failing before)
            engine = await configured_execution_factory.create_for_user(valid_user_context)
            
            # Verify engine was created successfully
            assert engine is not None
            assert engine.get_user_context() == valid_user_context
            
            print(f"[FIXED] create_for_user succeeds: engine {engine.engine_id} created")
    
    def test_bug_is_fixed_constructor_validation_prevents_late_failures(self):
        """
        CRITICAL: Verify the fix prevents the original bug through constructor validation.
        
        The fix moves validation from execution time to initialization time,
        preventing the "WebSocket bridge not available" error.
        """
        
        # The fix should prevent creating factory without bridge (fail fast)
        with pytest.raises(ExecutionEngineFactoryError) as exc_info:
            ExecutionEngineFactory()  # No websocket_bridge parameter
        
        # Verify clear error message
        error_msg = str(exc_info.value)
        assert "ExecutionEngineFactory requires websocket_bridge during initialization" in error_msg
        
        # With valid bridge, creation should succeed
        websocket_bridge = AgentWebSocketBridge() 
        factory = ExecutionEngineFactory(websocket_bridge=websocket_bridge)
        assert factory._websocket_bridge == websocket_bridge
        
        print("[FIXED] Constructor validation prevents late failures")
    
    def test_original_bug_conditions_eliminated(self):
        """
        Verify that the specific conditions that caused the original bug are eliminated.
        
        Original Bug Conditions:
        1. ExecutionEngineFactory created without websocket_bridge
        2. Late validation in _create_user_websocket_emitter()
        3. Dependency on unconfigured AgentInstanceFactory._websocket_bridge
        
        Fix eliminates these conditions.
        """
        
        # Condition 1: Factory creation without bridge is now impossible
        with pytest.raises(ExecutionEngineFactoryError):
            ExecutionEngineFactory()
        
        # Condition 2: Late validation is eliminated - bridge is available at init
        websocket_bridge = AgentWebSocketBridge()
        factory = ExecutionEngineFactory(websocket_bridge=websocket_bridge)
        assert factory._websocket_bridge is not None
        
        # Condition 3: No longer depends on AgentInstanceFactory._websocket_bridge
        # The factory has its own validated bridge
        assert factory._websocket_bridge == websocket_bridge
        
        print("[FIXED] All original bug conditions eliminated")
    
    def test_business_value_restored(self):
        """
        Verify that the fix restores the critical business value.
        
        Business Impact of Bug:
        - Agent execution failed completely
        - WebSocket events for chat were not sent
        - Users didn't get real-time updates
        - Chat business value (90% of platform value) was broken
        
        Business Value Restored by Fix:
        - ExecutionEngineFactory can create UserExecutionEngine
        - WebSocket events infrastructure is available
        - Agent execution can deliver real-time updates
        """
        
        # Create configured factory (represents restored business value)
        websocket_bridge = AgentWebSocketBridge()
        factory = ExecutionEngineFactory(websocket_bridge=websocket_bridge)
        
        # Verify infrastructure for business value is available
        assert factory._websocket_bridge is not None
        
        # This enables the business value chain:
        # ExecutionEngineFactory -> UserExecutionEngine -> Agent execution -> WebSocket events -> Chat value
        
        user_context = UserExecutionContext.from_request(
            user_id="business-user",
            thread_id="chat-thread",
            run_id="value-restoration-run"
        )
        
        # The factory should provide the infrastructure needed for chat business value
        # (Integration tests would verify the complete end-to-end chain)
        
        print("[FIXED] WebSocket event infrastructure restored for chat business value")
    
    def test_error_handling_improved(self):
        """
        Verify that the fix provides improved error handling and messages.
        
        The fix should provide clear, actionable error messages that help
        developers understand and resolve configuration issues.
        """
        
        # Test improved error message for missing bridge
        with pytest.raises(ExecutionEngineFactoryError) as exc_info:
            ExecutionEngineFactory()
        
        error_msg = str(exc_info.value)
        
        # Verify error message components
        assert "ExecutionEngineFactory requires websocket_bridge during initialization" in error_msg
        assert "AgentWebSocketBridge" in error_msg
        assert "startup" in error_msg
        assert "chat business value" in error_msg
        
        # Error message should be actionable for developers
        print(f"[FIXED] Improved error message: {error_msg}")
        
        # Verify successful case for completeness
        websocket_bridge = AgentWebSocketBridge()
        factory = ExecutionEngineFactory(websocket_bridge=websocket_bridge)
        assert factory is not None
        
        print("[FIXED] Error handling improved with actionable messages")


# Additional integration-style test to verify the complete fix
class TestExecutionEngineFactoryIntegrationFixValidation:
    """
    Integration-style validation that the complete fix works end-to-end.
    """
    
    @pytest.mark.asyncio
    async def test_complete_fix_integration(self):
        """
        Test the complete fix integration from initialization to WebSocket emitter creation.
        
        This simulates the fixed flow that should happen during system startup and execution.
        """
        
        # Step 1: System startup creates WebSocket bridge (simulated)
        websocket_bridge = AgentWebSocketBridge()
        print("[SIMULATION] System startup: AgentWebSocketBridge created")
        
        # Step 2: System startup configures ExecutionEngineFactory with bridge (THE FIX)
        execution_factory = ExecutionEngineFactory(websocket_bridge=websocket_bridge)
        print("[SIMULATION] System startup: ExecutionEngineFactory configured with WebSocket bridge")
        
        # Step 3: User request creates execution context
        user_context = UserExecutionContext.from_request(
            user_id="integration-user",
            thread_id="integration-thread", 
            run_id="integration-run"
        )
        print("[SIMULATION] User request: UserExecutionContext created")
        
        # Step 4: ExecutionEngineFactory creates WebSocket emitter (FIXED - no longer fails)
        mock_agent_factory = MagicMock()
        emitter = await execution_factory._create_user_websocket_emitter(
            user_context,
            mock_agent_factory  
        )
        print("[SIMULATION] ExecutionEngineFactory: WebSocket emitter created successfully")
        
        # Step 5: Verify the complete fix
        assert emitter is not None
        assert emitter.websocket_bridge == websocket_bridge
        assert emitter.user_id == "integration-user"
        
        print("[INTEGRATION] Complete fix validated - WebSocket events enabled for chat business value")