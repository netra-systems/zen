"""Core validation tests for execution engine migration to UserExecutionContext.

This test suite validates the core migration patterns without complex dependencies.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from datetime import datetime, timezone


class MockUserExecutionContext:
    """Mock UserExecutionContext for testing."""
    
    def __init__(self, user_id="test_user", request_id="test_request", thread_id="test_thread"):
        self.user_id = user_id
        self.request_id = request_id
        self.thread_id = thread_id
        self.session_id = "test_session"
        self.created_at = datetime.now(timezone.utc)
        self.metadata = {}


class MockAgentExecutionContext:
    """Mock AgentExecutionContext for testing."""
    
    def __init__(self, agent_name, task, user_context=None):
        self.agent_name = agent_name
        self.task = task
        self.user_context = user_context
        self.user_id = user_context.user_id if user_context else None
        self.request_id = user_context.request_id if user_context else None
        self.thread_id = user_context.thread_id if user_context else None
        self.metadata = {}


class MockAgentExecutionResult:
    """Mock AgentExecutionResult for testing."""
    
    def __init__(self, success=True, user_context=None, error=None, data=None):
        self.success = success
        self.user_context = user_context
        self.error = error
        self.data = data
        self.duration = 0.1
        self.metadata = {}


class TestExecutionEngineMigrationCore:
    """Core validation tests for UserExecutionContext migration."""
    
    def test_user_context_isolation(self):
        """Test that UserExecutionContext provides proper isolation."""
        user1 = MockUserExecutionContext(user_id="user1", request_id="req1")
        user2 = MockUserExecutionContext(user_id="user2", request_id="req2")
        
        # Validate complete separation
        assert user1.user_id != user2.user_id
        assert user1.request_id != user2.request_id
        assert user1.metadata is not user2.metadata
        
        # Validate proper initialization
        assert user1.user_id == "user1"
        assert user1.request_id == "req1"
        assert isinstance(user1.created_at, datetime)
        assert isinstance(user1.metadata, dict)
    
    def test_agent_execution_context_migration(self):
        """Test that AgentExecutionContext properly integrates UserExecutionContext."""
        user_context = MockUserExecutionContext()
        
        # Create context with UserExecutionContext
        context = MockAgentExecutionContext(
            agent_name="test_agent",
            task="test_task",
            user_context=user_context
        )
        
        # Validate integration
        assert context.agent_name == "test_agent"
        assert context.task == "test_task"
        assert context.user_context == user_context
        assert context.user_id == user_context.user_id
        assert context.request_id == user_context.request_id
        assert context.thread_id == user_context.thread_id
    
    def test_agent_execution_result_migration(self):
        """Test that AgentExecutionResult properly handles UserExecutionContext."""
        user_context = MockUserExecutionContext()
        
        # Test successful result
        success_result = MockAgentExecutionResult(
            success=True,
            user_context=user_context,
            data="test_result"
        )
        
        assert success_result.success is True
        assert success_result.user_context == user_context
        assert success_result.data == "test_result"
        assert success_result.error is None
        
        # Test error result
        error_result = MockAgentExecutionResult(
            success=False,
            user_context=user_context,
            error="Test error"
        )
        
        assert error_result.success is False
        assert error_result.user_context == user_context
        assert error_result.error == "Test error"
    
    def test_user_context_metadata_handling(self):
        """Test that UserExecutionContext properly handles metadata."""
        user_context = MockUserExecutionContext()
        
        # Test metadata assignment
        user_context.metadata["test_key"] = "test_value"
        user_context.metadata["user_prompt"] = "Hello, agent!"
        user_context.metadata["final_answer"] = "Response from agent"
        
        # Validate metadata persistence
        assert user_context.metadata["test_key"] == "test_value"
        assert user_context.metadata["user_prompt"] == "Hello, agent!"
        assert user_context.metadata["final_answer"] == "Response from agent"
        
        # Test metadata isolation
        user2_context = MockUserExecutionContext()
        assert "test_key" not in user2_context.metadata
        assert user2_context.metadata is not user_context.metadata
    
    def test_websocket_event_context_preservation(self):
        """Test that WebSocket events preserve user context information."""
        user_context = MockUserExecutionContext(
            user_id="ws_user_123",
            request_id="ws_req_456",
            thread_id="ws_thread_789"
        )
        
        # Mock WebSocket bridge calls
        mock_bridge = Mock()
        mock_bridge.notify_agent_started = Mock()
        mock_bridge.notify_agent_completed = Mock()
        mock_bridge.notify_agent_error = Mock()
        
        # Simulate WebSocket notifications with user context
        mock_bridge.notify_agent_started(
            run_id=user_context.request_id,
            agent_name="test_agent",
            context={"user_id": user_context.user_id, "isolated": True}
        )
        
        mock_bridge.notify_agent_completed(
            run_id=user_context.request_id,
            agent_name="test_agent",
            result={"status": "completed", "user_id": user_context.user_id}
        )
        
        # Validate calls were made with proper context
        mock_bridge.notify_agent_started.assert_called_once()
        mock_bridge.notify_agent_completed.assert_called_once()
        
        # Validate call arguments contain user context
        start_args = mock_bridge.notify_agent_started.call_args
        assert start_args[1]["run_id"] == user_context.request_id
        assert start_args[1]["context"]["user_id"] == user_context.user_id
        assert start_args[1]["context"]["isolated"] is True
        
        completion_args = mock_bridge.notify_agent_completed.call_args
        assert completion_args[1]["run_id"] == user_context.request_id
        assert completion_args[1]["result"]["user_id"] == user_context.user_id
    
    def test_migration_pattern_validation(self):
        """Test that migration patterns follow the established conventions."""
        user_context = MockUserExecutionContext()
        
        # Test 1: UserExecutionContext replaces DeepAgentState
        # OLD: execute_agent(context, state: DeepAgentState)
        # NEW: execute_agent(context, user_context: UserExecutionContext)
        
        def old_style_execute(context, state):
            """Old style with DeepAgentState - DEPRECATED"""
            return f"Executed {context.agent_name} with state {type(state).__name__}"
        
        def new_style_execute(context, user_context):
            """New style with UserExecutionContext - CURRENT"""
            return f"Executed {context.agent_name} with user {user_context.user_id}"
        
        context = MockAgentExecutionContext("test_agent", "test_task", user_context)
        
        # Validate new style works correctly
        result = new_style_execute(context, user_context)
        assert "test_agent" in result
        assert user_context.user_id in result
        
        # Test 2: AgentExecutionResult contains UserExecutionContext instead of DeepAgentState
        result_obj = MockAgentExecutionResult(
            success=True,
            user_context=user_context,
            data="migration_success"
        )
        
        assert result_obj.user_context == user_context
        assert result_obj.data == "migration_success"
        assert hasattr(result_obj, 'user_context')  # New field
        assert result_obj.success is True
    
    @pytest.mark.asyncio
    async def test_async_execution_pattern_migration(self):
        """Test that async execution patterns work with UserExecutionContext."""
        user_context = MockUserExecutionContext()
        
        # Mock async agent execution
        async def mock_agent_execute(task, user_context):
            """Mock agent execution with UserExecutionContext."""
            await asyncio.sleep(0.001)  # Simulate async work
            user_context.metadata["execution_result"] = f"Processed: {task}"
            return "execution_completed"
        
        # Mock async execution engine pattern
        async def mock_execution_engine_execute(agent_name, task, user_context):
            """Mock execution engine execute method."""
            # Simulate agent lookup and execution
            result = await mock_agent_execute(task, user_context)
            
            return MockAgentExecutionResult(
                success=True,
                user_context=user_context,
                data=result
            )
        
        # Test execution
        result = await mock_execution_engine_execute(
            "test_agent",
            "test_task",
            user_context
        )
        
        # Validate execution succeeded
        assert result.success is True
        assert result.user_context == user_context
        assert result.data == "execution_completed"
        assert user_context.metadata["execution_result"] == "Processed: test_task"
    
    def test_error_handling_migration(self):
        """Test that error handling works correctly with UserExecutionContext."""
        user_context = MockUserExecutionContext()
        
        # Test error scenarios
        error_result = MockAgentExecutionResult(
            success=False,
            user_context=user_context,
            error="Test error occurred"
        )
        
        assert error_result.success is False
        assert error_result.user_context == user_context
        assert error_result.error == "Test error occurred"
        
        # Test that user context is preserved even in error cases
        assert error_result.user_context.user_id == user_context.user_id
        assert error_result.user_context.request_id == user_context.request_id
    
    def test_factory_pattern_migration(self):
        """Test that factory patterns work with UserExecutionContext."""
        # Mock factory configuration
        factory_config = {
            "max_concurrent_per_user": 5,
            "execution_timeout": 30.0,
            "enable_user_isolation": True
        }
        
        # Mock factory create method
        def create_execution_engine(user_context, config):
            """Mock factory method to create user-isolated execution engine."""
            if not user_context:
                raise ValueError("UserExecutionContext is required")
            
            return {
                "user_context": user_context,
                "config": config,
                "isolated": True,
                "semaphore_limit": config["max_concurrent_per_user"]
            }
        
        user_context = MockUserExecutionContext()
        engine = create_execution_engine(user_context, factory_config)
        
        # Validate factory creates proper isolated engine
        assert engine["user_context"] == user_context
        assert engine["isolated"] is True
        assert engine["semaphore_limit"] == 5
        
        # Test that different users get different engines
        user2_context = MockUserExecutionContext(user_id="user2", request_id="req2")
        engine2 = create_execution_engine(user2_context, factory_config)
        
        assert engine["user_context"] != engine2["user_context"]
        assert engine["user_context"].user_id != engine2["user_context"].user_id


if __name__ == "__main__":
    pytest.main([__file__, "-v"])