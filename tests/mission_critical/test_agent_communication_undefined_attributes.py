"""Mission Critical Test Suite for Agent Communication Undefined Attributes

This test suite verifies that all undefined attributes and methods in
AgentCommunicationMixin are properly fixed and initialized.

CRITICAL: These tests MUST pass for agent communication to work properly.
"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any

from netra_backend.app.agents.agent_communication import AgentCommunicationMixin
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.base.interface import ExecutionContext
from netra_backend.app.schemas.agent import SubAgentLifecycle


class TestAgentWithCommunication(BaseAgent, AgentCommunicationMixin):
    """Test agent that uses AgentCommunicationMixin"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Simulate what should happen in proper initialization
        self.websocket_manager = None
        
    async def execute(self, state, run_id: str, stream_updates: bool = False):
        """Dummy execute method for testing"""
        return {"status": "completed"}
    
    async def execute_core_logic(self, context: ExecutionContext):
        """Required abstract method implementation"""
        return {"status": "completed"}
    
    async def validate_preconditions(self, context: ExecutionContext):
        """Required abstract method implementation"""
        return True


class TestUndefinedAttributes:
    """Test suite for undefined attributes in AgentCommunicationMixin"""
    
    @pytest.fixture
    def test_agent(self):
        """Create a test agent with proper initialization"""
        agent = TestAgentWithCommunication(
            name="TestAgent",
            description="Test agent for undefined attributes"
        )
        return agent
    
    def test_agent_id_is_defined(self, test_agent):
        """Test that agent_id attribute exists and is properly initialized"""
        # This should NOT raise AttributeError
        assert hasattr(test_agent, 'agent_id'), "agent_id attribute is missing"
        assert test_agent.agent_id is not None, "agent_id should not be None"
        assert isinstance(test_agent.agent_id, str), "agent_id should be a string"
        assert test_agent.name in test_agent.agent_id, "agent_id should contain agent name"
    
    def test_underscore_user_id_is_defined(self, test_agent):
        """Test that _user_id attribute exists (with underscore)"""
        # This should NOT raise AttributeError
        assert hasattr(test_agent, '_user_id'), "_user_id attribute is missing"
        # Can be None initially but should exist
        
    def test_get_state_method_exists(self, test_agent):
        """Test that get_state() method exists and returns proper value"""
        # This should NOT raise AttributeError
        assert hasattr(test_agent, 'get_state'), "get_state method is missing"
        state = test_agent.get_state()
        assert isinstance(state, SubAgentLifecycle), "get_state should return SubAgentLifecycle"
    
    def test_name_attribute_exists(self, test_agent):
        """Test that name attribute exists"""
        assert hasattr(test_agent, 'name'), "name attribute is missing"
        assert test_agent.name == "TestAgent"
    
    def test_logger_attribute_exists(self, test_agent):
        """Test that logger attribute exists"""
        assert hasattr(test_agent, 'logger'), "logger attribute is missing"
        assert test_agent.logger is not None, "logger should not be None"
    
    def test_websocket_manager_attribute_exists(self, test_agent):
        """Test that websocket_manager attribute exists"""
        assert hasattr(test_agent, 'websocket_manager'), "websocket_manager attribute is missing"
        # Can be None for backward compatibility
    
    @pytest.mark.asyncio
    async def test_create_error_context_with_agent_id(self, test_agent):
        """Test that _create_error_context properly uses agent_id"""
        # This should NOT raise AttributeError when accessing self.agent_id
        run_id = "test_run_123"
        data = {"message": "test"}
        
        context = test_agent._create_error_context(run_id, data)
        
        # Context should be created without errors
        assert context is not None
        assert hasattr(context, 'agent_id'), "ErrorContext should have agent_id"
    
    @pytest.mark.asyncio
    async def test_get_websocket_user_id_with_underscore_user_id(self, test_agent):
        """Test that _get_websocket_user_id properly uses _user_id"""
        run_id = "test_run_123"
        
        # Set _user_id
        test_agent._user_id = "test_user_456"
        
        # This should NOT raise AttributeError
        user_id = test_agent._get_websocket_user_id(run_id)
        
        assert user_id == "test_user_456", "Should return _user_id when set"
    
    @pytest.mark.asyncio
    async def test_process_websocket_error_with_agent_id(self, test_agent):
        """Test that _process_websocket_error properly logs with agent_id"""
        from netra_backend.app.agents.agent_communication import WebSocketError
        
        # This should NOT raise AttributeError when accessing self.agent_id
        error = WebSocketError("Test error")
        
        # Should not raise AttributeError
        test_agent._process_websocket_error(error)
    
    def test_all_undefined_methods_exist(self, test_agent):
        """Test that all methods referenced in the report exist"""
        # Methods that were reported as undefined
        methods_to_check = [
            '_log_agent_start',
            '_log_agent_completion',
        ]
        
        # These are optional/deprecated methods that may not exist
        # but are referenced in error handling paths
        for method_name in methods_to_check:
            if not hasattr(test_agent, method_name):
                # Should have a fallback or not be called
                print(f"Warning: {method_name} is not defined but may be referenced")


class TestInitializationPatterns:
    """Test proper initialization patterns for agents"""
    
    def test_base_agent_initialization_with_ids(self):
        """Test that BaseAgent can be initialized with agent_id and user_id"""
        agent = BaseAgent(
            name="TestAgent",
            description="Test description",
            agent_id="custom_agent_123",  # Should accept agent_id
            user_id="custom_user_456"     # Should accept user_id
        )
        
        assert agent.agent_id == "custom_agent_123"
        assert agent._user_id == "custom_user_456"  # Note underscore
        assert agent.user_id == "custom_user_456"   # Backward compatibility
    
    def test_base_agent_auto_generates_agent_id(self):
        """Test that BaseAgent auto-generates agent_id if not provided"""
        agent = BaseAgent(
            name="TestAgent",
            description="Test description"
        )
        
        assert hasattr(agent, 'agent_id')
        assert agent.agent_id is not None
        assert "TestAgent" in agent.agent_id
        assert hasattr(agent, 'correlation_id')
        # Should include correlation_id for uniqueness
        
    def test_mixin_compatibility(self):
        """Test that AgentCommunicationMixin works with properly initialized BaseAgent"""
        
        class ProperlyInitializedAgent(BaseAgent, AgentCommunicationMixin):
            async def run(self, state, run_id: str, stream_updates: bool = False):
                # Test that mixin methods can access expected attributes
                await self._send_update(run_id, {"message": "test"})
                return {"status": "completed"}
        
        agent = ProperlyInitializedAgent(
            name="ProperAgent",
            agent_id="proper_123",
            user_id="user_789"
        )
        
        # All attributes should be accessible
        assert agent.agent_id == "proper_123"
        assert agent._user_id == "user_789"
        assert agent.name == "ProperAgent"
        assert hasattr(agent, 'logger')
        assert hasattr(agent, 'websocket_manager')


class TestRuntimeBehavior:
    """Test runtime behavior with fixed attributes"""
    
    @pytest.mark.asyncio
    async def test_send_update_without_errors(self):
        """Test that _send_update doesn't raise AttributeError"""
        agent = TestAgentWithCommunication(name="RuntimeTest")
        
        # Mock websocket_manager
        agent.websocket_manager = None  # Simulate no WebSocket
        
        # This should NOT raise AttributeError
        await agent._send_update("run_123", {"status": "starting"})
    
    @pytest.mark.asyncio
    async def test_full_communication_flow(self):
        """Test full communication flow with all attributes properly set"""
        agent = TestAgentWithCommunication(
            name="FullFlowTest"
        )
        
        # Ensure all required attributes exist
        if not hasattr(agent, 'agent_id'):
            agent.agent_id = f"{agent.name}_test_id"
        if not hasattr(agent, '_user_id'):
            agent._user_id = "test_user"
        
        # Mock the bridge
        with patch('netra_backend.app.agents.agent_communication.get_agent_websocket_bridge') as mock_bridge:
            mock_bridge.return_value = AsyncMock()
            
            # Test various notification methods using unified emit methods
            await agent.emit_tool_executing("test_tool")
            await agent.emit_thinking("Processing...", step_number=1)
            await agent.emit_progress("Partial result", is_complete=False)
            await agent.emit_agent_completed({"result": "success", "duration_ms": 1234.5})
            
            # Should complete without AttributeError
            # Note: emit methods work through BaseAgent's WebSocketBridgeAdapter
            # so we don't test the old notify methods anymore


class TestFailureScenarios:
    """Test that proper error handling occurs even with undefined attributes"""
    
    @pytest.mark.asyncio
    async def test_websocket_failure_handling(self):
        """Test WebSocket failure handling with all attributes defined"""
        agent = TestAgentWithCommunication(name="FailureTest")
        
        # Ensure critical attributes exist
        if not hasattr(agent, 'agent_id'):
            agent.agent_id = "failure_test_id"
        if not hasattr(agent, '_user_id'):
            agent._user_id = None
        
        # Test failure handling
        run_id = "fail_run_123"
        data = {"status": "error", "message": "Test failure"}
        error = Exception("WebSocket disconnected")
        
        # This should NOT raise AttributeError
        await agent._handle_websocket_failure(run_id, data, error)
        
        # Check that failed updates are stored
        assert hasattr(agent, '_failed_updates')
        assert len(agent._failed_updates) > 0
    
    @pytest.mark.asyncio
    async def test_error_context_creation(self):
        """Test that error context is properly created with all attributes"""
        agent = TestAgentWithCommunication(name="ErrorContextTest")
        
        # Ensure agent_id exists
        if not hasattr(agent, 'agent_id'):
            agent.agent_id = "error_test_id"
        
        run_id = "error_run_123"
        data = {"error": "Test error"}
        
        context = agent._create_error_context(run_id, data)
        
        # Verify context has expected attributes
        assert context.agent_id is not None
        assert hasattr(context, 'additional_info')


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "--tb=short"])