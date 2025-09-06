from unittest.mock import AsyncMock, Mock, patch, MagicMock

"""Execution tests for SupervisorAgent - execution methods and hook management."""

import sys
from pathlib import Path
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import TestDatabaseManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

# Test framework import - using pytest fixtures instead

import asyncio

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.agents.state import DeepAgentState

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
        mock_result = mock_result_instance  # Initialize appropriate service
        mock_result.success = True
        supervisor.reliability_manager.execute_with_reliability.return_value = mock_result
        
        # Create input state
        state = DeepAgentState(
            user_request="test query",
            chat_thread_id="thread-123",
            user_id="user-456"
        )
        run_id = "run-789"
        
        # Execute
        await supervisor.execute(state, run_id, stream_updates=True)
        
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
        mock_result = mock_result_instance  # Initialize appropriate service
        mock_result.success = True
        supervisor.reliability_manager.execute_with_reliability.return_value = mock_result
        
        # Create minimal state - should use defaults for missing fields
        state = DeepAgentState(user_request="test query")
        run_id = "run-789"
        
        # Execute
        await supervisor.execute(state, run_id, stream_updates=True)
        
        # Verify modern execution pattern was used
        supervisor.reliability_manager.execute_with_reliability.assert_called_once()
        
        # Verify execution context was created properly
        args, kwargs = supervisor.reliability_manager.execute_with_reliability.call_args
        context = args[0]
        assert context.run_id == run_id
        # Note: Both user_id and thread_id will be None because the state explicitly has them as None
        # The getattr default is only used when the attribute doesn't exist, not when it's None
        assert context.user_id is None  # Explicitly None in state
        assert context.thread_id is None  # Explicitly None in state
    
    def test_create_execution_context(self):
        """Test execution context creation for modern pattern."""
        # Mock: LLM service isolation for fast testing without API calls or rate limits
        llm_manager = Mock(spec=LLMManager)
        # Mock: Database session isolation for transaction testing without real database dependency
        db_session = Mock(spec=AsyncSession)
        # Mock: WebSocket connection isolation for testing without network overhead
        websocket_manager = UnifiedWebSocketManager()
        # Mock: Tool dispatcher isolation for agent testing without real tool execution
        tool_dispatcher = Mock(spec=ToolDispatcher)
        
        supervisor = SupervisorAgent(db_session, llm_manager, websocket_manager, tool_dispatcher)
        
        # Create state
        state = DeepAgentState(
            user_request="test query",
            chat_thread_id="thread-123",
            user_id="user-456"
        )
        
        # Create execution context using modern pattern
        context = supervisor._create_supervisor_execution_context(state, "run-789", True)
        
        # Verify context structure
        assert context.thread_id == "thread-123"
        assert context.user_id == "user-456"
        assert context.run_id == "run-789"
        assert context.stream_updates == True
        assert context.agent_name == "Supervisor"
    
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
        
        # Mock workflow executor that run() actually uses
        supervisor.workflow_executor.execute_workflow_steps = AsyncMock(
            return_value=DeepAgentState(user_request="test")
        )
        
        # Mock flow logger
        supervisor.flow_logger.generate_flow_id = Mock(return_value="flow_test")
        supervisor.flow_logger.start_flow = start_flow_instance  # Initialize appropriate service
        supervisor.flow_logger.complete_flow = complete_flow_instance  # Initialize appropriate service
        
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
        
        # Verify lock was used
        assert lock_acquired
        assert isinstance(result, DeepAgentState)
    
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
        mock_result = mock_result_instance  # Initialize appropriate service
        mock_result.success = True
        supervisor.reliability_manager.execute_with_reliability.return_value = mock_result
        
        # Test data
        state = DeepAgentState(user_request="test")
        context = supervisor._create_supervisor_execution_context(state, "test-run", True)
        
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
        
        # Create updated state from execution result
        updated_state = DeepAgentState(
            user_request="updated query",
            triage_result={"category": "optimization"}
        )
        
        # Mock successful result
        mock_result = mock_result_instance  # Initialize appropriate service
        mock_result.success = True
        mock_result.result = {"supervisor_result": "completed", "updated_state": updated_state}
        supervisor.reliability_manager.execute_with_reliability.return_value = mock_result
        
        # Create original state
        original_state = DeepAgentState(user_request="original query")
        
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
        
        # Mock workflow executor which is what run() actually uses
        mock_state = DeepAgentState(user_request="test query")
        supervisor.workflow_executor.execute_workflow_steps = AsyncMock(return_value=mock_state)
        
        # Mock flow logger
        supervisor.flow_logger.generate_flow_id = Mock(return_value="flow_test")
        supervisor.flow_logger.start_flow = start_flow_instance  # Initialize appropriate service
        supervisor.flow_logger.complete_flow = complete_flow_instance  # Initialize appropriate service
        
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
        
        # Create state
        state = DeepAgentState(user_request="test")
        
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
        
        state = DeepAgentState(user_request="test")
        
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
        
        state = DeepAgentState(user_request="test")
        
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
        
        state = DeepAgentState(user_request="test")
        
        # Execute non-existent hooks - should not crash
        await supervisor._run_hooks("nonexistent_event", state)
        
        # Should complete without error
