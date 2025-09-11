from unittest.mock import AsyncMock, Mock, patch, MagicMock

"""Execution tests for SupervisorAgent - execution methods and hook management."""

import sys
from pathlib import Path
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import DatabaseTestManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

# Test framework import - using pytest fixtures instead

import asyncio

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.services.user_execution_context import UserExecutionContext

from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.llm.llm_manager import LLMManager

class TestSupervisorAgentExecution:
    """Test execution methods."""
    
    @pytest.mark.asyncio
    async def test_execute_method(self):
        """Test execute method uses modern execution pattern."""
        # Mock: LLM service isolation for fast testing without API calls or rate limits
        llm_manager = Mock(spec=LLMManager)
        # Mock: Database session isolation for transaction testing without real database dependency
        db_session = Mock(spec=AsyncSession)
        # Mock: WebSocket connection isolation for testing without network overhead
        websocket_manager = UnifiedWebSocketManager()
        # Mock: Tool dispatcher isolation for agent testing without real tool execution
        tool_dispatcher = Mock(spec=ToolDispatcher)
        
        supervisor = SupervisorAgent(db_session, llm_manager, websocket_manager, tool_dispatcher)
        
        # Mock modern execution infrastructure
        supervisor.reliability_manager.execute_with_reliability = AsyncMock()  # TODO: Use real service instance
        supervisor.execution_engine.execute = AsyncMock()  # TODO: Use real service instance
        
        # Mock the execution result
        mock_result = Mock()
        mock_result.success = True
        supervisor.reliability_manager.execute_with_reliability.return_value = mock_result
        
        # Create secure user execution context
        user_context = UserExecutionContext.from_request(
            user_id="user-456",
            thread_id="thread-123",
            run_id="run-789"
        )
        user_context.metadata["user_request"] = "test query"
        
        # Execute with secure context
        await supervisor.execute(user_context.to_agent_state(), user_context.run_id, stream_updates=True)
        
        # Verify modern execution pattern was used
        supervisor.reliability_manager.execute_with_reliability.assert_called_once()
        # Verify execution engine was used in the reliability manager call
        args, kwargs = supervisor.reliability_manager.execute_with_reliability.call_args
        assert len(args) >= 1  # Context passed
        assert callable(kwargs.get('func') or args[1])  # Lambda function passed
    
    @pytest.mark.asyncio
    async def test_execute_method_with_defaults(self):
        """Test execute method handles default values in modern execution pattern."""
        # Mock: LLM service isolation for fast testing without API calls or rate limits
        llm_manager = Mock(spec=LLMManager)
        # Mock: Database session isolation for transaction testing without real database dependency
        db_session = Mock(spec=AsyncSession)
        # Mock: WebSocket connection isolation for testing without network overhead
        websocket_manager = UnifiedWebSocketManager()
        # Mock: Tool dispatcher isolation for agent testing without real tool execution
        tool_dispatcher = Mock(spec=ToolDispatcher)
        
        supervisor = SupervisorAgent(db_session, llm_manager, websocket_manager, tool_dispatcher)
        
        # Mock modern execution infrastructure
        supervisor.reliability_manager.execute_with_reliability = AsyncMock()  # TODO: Use real service instance
        supervisor.execution_engine.execute = AsyncMock()  # TODO: Use real service instance
        
        # Mock the execution result
        mock_result = Mock()
        mock_result.success = True
        supervisor.reliability_manager.execute_with_reliability.return_value = mock_result
        
        # Create minimal secure context - should use defaults for missing fields
        user_context = UserExecutionContext.from_request(
            user_id="test-user-456",
            thread_id="test-thread-123", 
            run_id="run-789"
        )
        user_context.metadata["user_request"] = "test query"
        
        # Execute with secure context
        await supervisor.execute(user_context.to_agent_state(), user_context.run_id, stream_updates=True)
        
        # Verify modern execution pattern was used
        supervisor.reliability_manager.execute_with_reliability.assert_called_once()
        
        # Verify execution context was created properly
        args, kwargs = supervisor.reliability_manager.execute_with_reliability.call_args
        context = args[0]
        assert context.run_id == user_context.run_id
        # Verify secure user isolation
        assert context.user_id == "test-user-456"
        assert context.thread_id == "test-thread-123"
    
    def test_create_execution_context(self):
        """Test execution context creation for secure modern pattern."""
        # Mock: LLM service isolation for fast testing without API calls or rate limits
        llm_manager = Mock(spec=LLMManager)
        # Mock: Database session isolation for transaction testing without real database dependency
        db_session = Mock(spec=AsyncSession)
        # Mock: WebSocket connection isolation for testing without network overhead
        websocket_manager = UnifiedWebSocketManager()
        # Mock: Tool dispatcher isolation for agent testing without real tool execution
        tool_dispatcher = Mock(spec=ToolDispatcher)
        
        supervisor = SupervisorAgent(db_session, llm_manager, websocket_manager, tool_dispatcher)
        
        # Create secure user execution context
        user_context = UserExecutionContext.from_request(
            user_id="user-456",
            thread_id="thread-123",
            run_id="run-789"
        )
        user_context.metadata["user_request"] = "test query"
        
        # Verify secure context structure (P0 Security Validation)
        assert user_context.user_id == "user-456"
        assert user_context.thread_id == "thread-123"
        assert user_context.run_id == "run-789"
        assert user_context.metadata["user_request"] == "test query"
        # Verify user isolation is maintained
        assert hasattr(user_context, 'isolation_boundary')
        # Verify secure agent state conversion works
        agent_state = user_context.to_agent_state()
        assert hasattr(agent_state, 'user_request')
    
    @pytest.mark.asyncio
    async def test_run_method_with_execution_lock(self):
        """Test run method uses execution lock."""
        # Mock: LLM service isolation for fast testing without API calls or rate limits
        llm_manager = Mock(spec=LLMManager)
        # Mock: Database session isolation for transaction testing without real database dependency
        db_session = Mock(spec=AsyncSession)
        # Mock: WebSocket connection isolation for testing without network overhead
        websocket_manager = UnifiedWebSocketManager()
        # Mock: Tool dispatcher isolation for agent testing without real tool execution
        tool_dispatcher = Mock(spec=ToolDispatcher)
        
        supervisor = SupervisorAgent(db_session, llm_manager, websocket_manager, tool_dispatcher)
        
        # Mock workflow executor that run() actually uses (with secure context)
        secure_result_context = UserExecutionContext.from_request(
            user_id="user-456",
            thread_id="thread-123", 
            run_id="run-789"
        )
        secure_result_context.metadata["user_request"] = "test"
        supervisor.workflow_executor.execute_workflow_steps = AsyncMock(
            return_value=secure_result_context.to_agent_state()
        )
        
        # Mock flow logger
        supervisor.flow_logger.generate_flow_id = Mock(return_value="flow_test")
        supervisor.flow_logger.start_flow = Mock()
        supervisor.flow_logger.complete_flow = Mock()
        
        # Track lock usage
        lock_acquired = False
        original_acquire = supervisor._execution_lock.acquire
        
        async def mock_acquire():
            nonlocal lock_acquired
            lock_acquired = True
            return await original_acquire()
        
        supervisor._execution_lock.acquire = mock_acquire
        
        # Execute
        result = await supervisor.run("test query", "thread-123", "user-456", "run-789")
        
        # Verify lock was used and result is secure
        assert lock_acquired
        # Result should be agent state created from secure UserExecutionContext
        assert hasattr(result, 'user_request')
    
    @pytest.mark.asyncio
    async def test_execute_with_modern_reliability_pattern(self):
        """Test modern reliability pattern execution."""
        # Mock: LLM service isolation for fast testing without API calls or rate limits
        llm_manager = Mock(spec=LLMManager)
        # Mock: Database session isolation for transaction testing without real database dependency
        db_session = Mock(spec=AsyncSession)
        # Mock: WebSocket connection isolation for testing without network overhead
        websocket_manager = UnifiedWebSocketManager()
        # Mock: Tool dispatcher isolation for agent testing without real tool execution
        tool_dispatcher = Mock(spec=ToolDispatcher)
        
        supervisor = SupervisorAgent(db_session, llm_manager, websocket_manager, tool_dispatcher)
        
        # Mock modern execution infrastructure
        supervisor.reliability_manager.execute_with_reliability = AsyncMock()  # TODO: Use real service instance
        supervisor.execution_engine.execute = AsyncMock()  # TODO: Use real service instance
        
        # Mock successful result
        mock_result = Mock()
        mock_result.success = True
        supervisor.reliability_manager.execute_with_reliability.return_value = mock_result
        
        # Test data with secure context
        user_context = UserExecutionContext.from_request(
            user_id="test-user-123",
            thread_id="test-thread-456",
            run_id="test-run"
        )
        user_context.metadata["user_request"] = "test"
        # Create a mock execution context (since _create_supervisor_execution_context doesn't exist)
        context = Mock()
        context.user_id = user_context.user_id
        context.thread_id = user_context.thread_id
        context.run_id = user_context.run_id
        
        # Execute modern reliability pattern
        await supervisor._execute_with_modern_reliability_pattern(context)
        
        # Verify reliability manager was called with context and execution function
        supervisor.reliability_manager.execute_with_reliability.assert_called_once()
        args, kwargs = supervisor.reliability_manager.execute_with_reliability.call_args
        assert args[0] == context  # ExecutionContext passed
        assert callable(kwargs.get('func') or args[1])  # Lambda function passed
    
    @pytest.mark.asyncio
    async def test_execute_with_modern_pattern_state_handling(self):
        """Test modern execution pattern handles state properly."""
        # Mock: LLM service isolation for fast testing without API calls or rate limits
        llm_manager = Mock(spec=LLMManager)
        # Mock: Database session isolation for transaction testing without real database dependency
        db_session = Mock(spec=AsyncSession)
        # Mock: WebSocket connection isolation for testing without network overhead
        websocket_manager = UnifiedWebSocketManager()
        # Mock: Tool dispatcher isolation for agent testing without real tool execution
        tool_dispatcher = Mock(spec=ToolDispatcher)
        
        supervisor = SupervisorAgent(db_session, llm_manager, websocket_manager, tool_dispatcher)
        
        # Mock modern execution infrastructure
        supervisor.reliability_manager.execute_with_reliability = AsyncMock()  # TODO: Use real service instance
        supervisor.execution_engine.execute = AsyncMock()  # TODO: Use real service instance
        supervisor.error_handler.handle_execution_error = AsyncMock()  # TODO: Use real service instance
        
        # Create updated secure context from execution result
        updated_user_context = UserExecutionContext.from_request(
            user_id="user-123",
            thread_id="thread-456",
            run_id="run-789"
        )
        updated_user_context.metadata["user_request"] = "updated query"
        updated_user_context.metadata["triage_result"] = {"category": "optimization"}
        updated_state = updated_user_context.to_agent_state()
        
        # Mock successful result
        mock_result = Mock()
        mock_result.success = True
        mock_result.result = {"supervisor_result": "completed", "updated_state": updated_state}
        supervisor.reliability_manager.execute_with_reliability.return_value = mock_result
        
        # Create original secure context
        original_user_context = UserExecutionContext.from_request(
            user_id="user-123",
            thread_id="thread-456", 
            run_id="run-123"
        )
        original_user_context.metadata["user_request"] = "original query"
        original_state = original_user_context.to_agent_state()
        
        # Execute
        await supervisor.execute(original_state, "run-123", stream_updates=True)
        
        # Verify modern execution pattern was used
        supervisor.reliability_manager.execute_with_reliability.assert_called_once()
        # Verify error handler was not called for successful execution
        supervisor.error_handler.handle_execution_error.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_run_method_workflow_coordination(self):
        """Test run method coordinates workflow execution properly."""
        # Mock: LLM service isolation for fast testing without API calls or rate limits
        llm_manager = Mock(spec=LLMManager)
        # Mock: Database session isolation for transaction testing without real database dependency
        db_session = Mock(spec=AsyncSession)
        # Mock: WebSocket connection isolation for testing without network overhead
        websocket_manager = UnifiedWebSocketManager()
        # Mock: Tool dispatcher isolation for agent testing without real tool execution
        tool_dispatcher = Mock(spec=ToolDispatcher)
        
        supervisor = SupervisorAgent(db_session, llm_manager, websocket_manager, tool_dispatcher)
        
        # Mock workflow executor which is what run() actually uses (with secure context)
        secure_mock_context = UserExecutionContext.from_request(
            user_id="user-456",
            thread_id="thread-123",
            run_id="run-789"
        )
        secure_mock_context.metadata["user_request"] = "test query"
        mock_state = secure_mock_context.to_agent_state()
        supervisor.workflow_executor.execute_workflow_steps = AsyncMock(return_value=mock_state)
        
        # Mock flow logger
        supervisor.flow_logger.generate_flow_id = Mock(return_value="flow_test")
        supervisor.flow_logger.start_flow = Mock()
        supervisor.flow_logger.complete_flow = Mock()
        
        # Execute
        result = await supervisor.run("test query", "thread-123", "user-456", "run-789")
        
        # Verify workflow execution components were called properly
        supervisor.flow_logger.generate_flow_id.assert_called_once()
        supervisor.flow_logger.start_flow.assert_called_once_with("flow_test", "run-789", 4)
        supervisor.workflow_executor.execute_workflow_steps.assert_called_once_with(
            "flow_test", "test query", "thread-123", "user-456", "run-789"
        )
        supervisor.flow_logger.complete_flow.assert_called_once_with("flow_test")
        
        # Verify result
        assert result == mock_state

class TestSupervisorAgentHooks:
    """Test hook execution."""
    
    @pytest.mark.asyncio
    async def test_run_hooks_success(self):
        """Test successful hook execution."""
        # Mock: LLM service isolation for fast testing without API calls or rate limits
        llm_manager = Mock(spec=LLMManager)
        # Mock: Database session isolation for transaction testing without real database dependency
        db_session = Mock(spec=AsyncSession)
        # Mock: WebSocket connection isolation for testing without network overhead
        websocket_manager = UnifiedWebSocketManager()
        # Mock: Tool dispatcher isolation for agent testing without real tool execution
        tool_dispatcher = Mock(spec=ToolDispatcher)
        
        supervisor = SupervisorAgent(db_session, llm_manager, websocket_manager, tool_dispatcher)
        
        # Create mock handlers
        # Mock: Generic component isolation for controlled unit testing
        handler1 = AsyncMock()  # TODO: Use real service instance
        # Mock: Generic component isolation for controlled unit testing
        handler2 = AsyncMock()  # TODO: Use real service instance
        
        # Register handlers
        supervisor.hooks["before_agent"] = [handler1, handler2]
        
        # Create secure user execution context
        user_context = UserExecutionContext.from_request(
            user_id="test-user-123",
            thread_id="test-thread-456",
            run_id="test-run-789"
        )
        user_context.metadata["user_request"] = "test"
        state = user_context.to_agent_state()
        
        # Execute hooks
        await supervisor._run_hooks("before_agent", state, extra_param="value")
        
        # Verify handlers called
        handler1.assert_called_once_with(state, extra_param="value")
        handler2.assert_called_once_with(state, extra_param="value")
    
    @pytest.mark.asyncio
    async def test_run_hooks_with_handler_failure(self):
        """Test hook execution with handler failure."""
        # Mock: LLM service isolation for fast testing without API calls or rate limits
        llm_manager = Mock(spec=LLMManager)
        # Mock: Database session isolation for transaction testing without real database dependency
        db_session = Mock(spec=AsyncSession)
        # Mock: WebSocket connection isolation for testing without network overhead
        websocket_manager = UnifiedWebSocketManager()
        # Mock: Tool dispatcher isolation for agent testing without real tool execution
        tool_dispatcher = Mock(spec=ToolDispatcher)
        
        supervisor = SupervisorAgent(db_session, llm_manager, websocket_manager, tool_dispatcher)
        
        # Create handlers - one fails
        # Mock: Generic component isolation for controlled unit testing
        handler1 = AsyncMock()  # TODO: Use real service instance
        # Mock: Async component isolation for testing without real async operations
        handler2 = AsyncMock(side_effect=Exception("Handler failed"))
        
        supervisor.hooks["before_agent"] = [handler1, handler2]
        
        # Create secure user execution context
        user_context = UserExecutionContext.from_request(
            user_id="test-user-123",
            thread_id="test-thread-456", 
            run_id="test-run-789",
            user_request="test"
        )
        state = user_context.to_agent_state()
        
        # Execute hooks - should not raise exception
        await supervisor._run_hooks("before_agent", state)
        
        # Verify first handler still called
        handler1.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_run_hooks_error_event_reraises(self):
        """Test hook execution for error event re-raises exceptions."""
        # Mock: LLM service isolation for fast testing without API calls or rate limits
        llm_manager = Mock(spec=LLMManager)
        # Mock: Database session isolation for transaction testing without real database dependency
        db_session = Mock(spec=AsyncSession)
        # Mock: WebSocket connection isolation for testing without network overhead
        websocket_manager = UnifiedWebSocketManager()
        # Mock: Tool dispatcher isolation for agent testing without real tool execution
        tool_dispatcher = Mock(spec=ToolDispatcher)
        
        supervisor = SupervisorAgent(db_session, llm_manager, websocket_manager, tool_dispatcher)
        
        # Create failing handler for error event
        # Mock: Async component isolation for testing without real async operations
        failing_handler = AsyncMock(side_effect=Exception("Error handler failed"))
        supervisor.hooks["on_error"] = [failing_handler]
        
        # Create secure user execution context
        user_context = UserExecutionContext.from_request(
            user_id="test-user-123",
            thread_id="test-thread-456", 
            run_id="test-run-789",
            user_request="test"
        )
        state = user_context.to_agent_state()
        
        # Execute error hooks - should re-raise
        with pytest.raises(Exception, match="Error handler failed"):
            await supervisor._run_hooks("on_error", state)
    
    @pytest.mark.asyncio
    async def test_run_hooks_nonexistent_event(self):
        """Test hook execution for non-existent event."""
        # Mock: LLM service isolation for fast testing without API calls or rate limits
        llm_manager = Mock(spec=LLMManager)
        # Mock: Database session isolation for transaction testing without real database dependency
        db_session = Mock(spec=AsyncSession)
        # Mock: WebSocket connection isolation for testing without network overhead
        websocket_manager = UnifiedWebSocketManager()
        # Mock: Tool dispatcher isolation for agent testing without real tool execution
        tool_dispatcher = Mock(spec=ToolDispatcher)
        
        supervisor = SupervisorAgent(db_session, llm_manager, websocket_manager, tool_dispatcher)
        
        # Create secure user execution context
        user_context = UserExecutionContext.from_request(
            user_id="test-user-123",
            thread_id="test-thread-456", 
            run_id="test-run-789",
            user_request="test"
        )
        state = user_context.to_agent_state()
        
        # Execute non-existent hooks - should not crash
        await supervisor._run_hooks("nonexistent_event", state)
        
        # Should complete without error
