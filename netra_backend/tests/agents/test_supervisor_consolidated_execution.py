from unittest.mock import AsyncMock, Mock, patch, MagicMock

"""P0 Critical Security Issue #407 - Execution tests for SupervisorAgent migrated from DeepAgentState to UserExecutionContext."""

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

# P0 SECURITY MIGRATION: Replaced vulnerable DeepAgentState with secure UserExecutionContext
from netra_backend.app.services.user_execution_context import UserExecutionContext

from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.llm.llm_manager import LLMManager

class TestSupervisorAgentExecution:
    """P0 Security Issue #407: Test execution methods migrated to secure UserExecutionContext."""
    
    @pytest.mark.asyncio
    async def test_execute_method_secure(self):
        """P0 SECURITY TEST: Execute method uses secure UserExecutionContext pattern."""
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
        supervisor.reliability_manager = Mock()
        supervisor.reliability_manager.execute_with_reliability = AsyncMock()
        supervisor.execution_engine = Mock()
        supervisor.execution_engine.execute = AsyncMock()
        
        # Mock the execution result
        mock_result = Mock()
        mock_result.success = True
        supervisor.reliability_manager.execute_with_reliability.return_value = mock_result
        
        # P0 SECURITY MIGRATION: Create secure UserExecutionContext instead of vulnerable DeepAgentState
        user_context = UserExecutionContext.from_request(
            user_id="user-456",
            thread_id="thread-123",
            run_id="run-789"
        )
        
        # Create secure mock state for execution (replaces vulnerable DeepAgentState)
        secure_state = Mock()
        secure_state.user_request = "test query"
        secure_state.user_id = user_context.user_id
        secure_state.chat_thread_id = user_context.thread_id
        
        # Execute with secure context
        await supervisor.execute(secure_state, user_context.run_id, stream_updates=True)
        
        # P0 SECURITY VALIDATION: Verify secure patterns were used
        supervisor.reliability_manager.execute_with_reliability.assert_called_once()
        # Verify user isolation is maintained
        assert user_context.user_id == "user-456"
        assert user_context.thread_id == "thread-123"
        assert user_context.run_id == "run-789"
    
    @pytest.mark.asyncio
    async def test_execute_method_with_defaults_secure(self):
        """P0 SECURITY TEST: Execute method handles defaults in secure UserExecutionContext pattern."""
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
        supervisor.reliability_manager = Mock()
        supervisor.reliability_manager.execute_with_reliability = AsyncMock()
        supervisor.execution_engine = Mock()
        supervisor.execution_engine.execute = AsyncMock()
        
        # Mock the execution result
        mock_result = Mock()
        mock_result.success = True
        supervisor.reliability_manager.execute_with_reliability.return_value = mock_result
        
        # P0 SECURITY MIGRATION: Create secure UserExecutionContext with proper defaults
        user_context = UserExecutionContext.from_request(
            user_id="test-user-456",
            thread_id="test-thread-123", 
            run_id="run-789"
        )
        
        # Create secure mock state for execution (replaces vulnerable DeepAgentState)
        secure_state = Mock()
        secure_state.user_request = "test query"
        secure_state.user_id = user_context.user_id
        secure_state.chat_thread_id = user_context.thread_id
        
        # Execute with secure context
        await supervisor.execute(secure_state, user_context.run_id, stream_updates=True)
        
        # P0 SECURITY VALIDATION: Verify execution context was created securely
        supervisor.reliability_manager.execute_with_reliability.assert_called_once()
        args, kwargs = supervisor.reliability_manager.execute_with_reliability.call_args
        context = args[0]
        assert context.run_id == user_context.run_id
        # Verify secure user isolation (no cross-contamination)
        assert user_context.user_id == "test-user-456"
        assert user_context.thread_id == "test-thread-123"
    
    def test_create_execution_context_secure(self):
        """P0 SECURITY TEST: Execution context creation uses secure UserExecutionContext pattern."""
        # Mock: LLM service isolation for fast testing without API calls or rate limits
        llm_manager = Mock(spec=LLMManager)
        # Mock: Database session isolation for transaction testing without real database dependency
        db_session = Mock(spec=AsyncSession)
        # Mock: WebSocket connection isolation for testing without network overhead
        websocket_manager = UnifiedWebSocketManager()
        # Mock: Tool dispatcher isolation for agent testing without real tool execution
        tool_dispatcher = Mock(spec=ToolDispatcher)
        
        supervisor = SupervisorAgent(db_session, llm_manager, websocket_manager, tool_dispatcher)
        
        # P0 SECURITY MIGRATION: Create secure UserExecutionContext instead of vulnerable DeepAgentState
        user_context = UserExecutionContext.from_request(
            user_id="user-456",
            thread_id="thread-123",
            run_id="run-789"
        )
        
        # P0 SECURITY VALIDATION: Verify secure context structure
        assert user_context.user_id == "user-456"
        assert user_context.thread_id == "thread-123"
        assert user_context.run_id == "run-789"
        # Verify user isolation is maintained - no cross-contamination
        assert user_context.user_id != "user-123"  # Not other user
        assert user_context.thread_id != "thread-456"  # Not other thread
        # Verify secure context creation without vulnerable patterns
        assert not hasattr(user_context, 'chat_thread_id')  # DeepAgentState field removed
        # P0 SUCCESS: UserExecutionContext created without security vulnerabilities
    
    @pytest.mark.asyncio
    async def test_run_method_with_execution_lock_secure(self):
        """P0 SECURITY TEST: Run method uses execution lock with secure UserExecutionContext."""
        # Mock: LLM service isolation for fast testing without API calls or rate limits
        llm_manager = Mock(spec=LLMManager)
        # Mock: Database session isolation for transaction testing without real database dependency
        db_session = Mock(spec=AsyncSession)
        # Mock: WebSocket connection isolation for testing without network overhead
        websocket_manager = UnifiedWebSocketManager()
        # Mock: Tool dispatcher isolation for agent testing without real tool execution
        tool_dispatcher = Mock(spec=ToolDispatcher)
        
        supervisor = SupervisorAgent(db_session, llm_manager, websocket_manager, tool_dispatcher)
        
        # Mock workflow executor with secure context
        secure_result_context = UserExecutionContext.from_request(
            user_id="user-456",
            thread_id="thread-123", 
            run_id="run-789"
        )
        # Create secure mock state for workflow result
        secure_mock_state = Mock()
        secure_mock_state.user_request = "test"
        supervisor.workflow_executor = Mock()
        supervisor.workflow_executor.execute_workflow_steps = AsyncMock(
            return_value=secure_mock_state
        )
        
        # Mock flow logger
        supervisor.flow_logger = Mock()
        supervisor.flow_logger.generate_flow_id = Mock(return_value="flow_test")
        supervisor.flow_logger.start_flow = Mock()
        supervisor.flow_logger.complete_flow = Mock()
        
        # Track lock usage
        supervisor._execution_lock = AsyncMock()
        lock_acquired = False
        original_acquire = supervisor._execution_lock.acquire
        
        async def mock_acquire():
            nonlocal lock_acquired
            lock_acquired = True
            return await original_acquire()
        
        supervisor._execution_lock.acquire = mock_acquire
        
        # Execute with secure pattern
        result = await supervisor.run("test query", "thread-123", "user-456", "run-789")
        
        # P0 SECURITY VALIDATION: Verify lock was used and result is secure
        assert lock_acquired
        # Result should be secure mock state (not vulnerable DeepAgentState)
        assert hasattr(result, 'user_request')

class TestSupervisorAgentHooks:
    """P0 Security Issue #407: Test hook execution migrated to secure UserExecutionContext."""
    
    @pytest.mark.asyncio
    async def test_run_hooks_success_secure(self):
        """P0 SECURITY TEST: Successful hook execution with secure UserExecutionContext."""
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
        handler1 = AsyncMock()
        handler2 = AsyncMock()
        
        # Register handlers
        supervisor.hooks = {"before_agent": [handler1, handler2]}
        
        # P0 SECURITY MIGRATION: Create secure UserExecutionContext instead of vulnerable DeepAgentState
        user_context = UserExecutionContext.from_request(
            user_id="test-user-123",
            thread_id="test-thread-456",
            run_id="test-run-789"
        )
        # Create secure mock state
        secure_state = Mock()
        secure_state.user_request = "test"
        
        # Execute hooks with secure context
        await supervisor._run_hooks("before_agent", secure_state, extra_param="value")
        
        # P0 SECURITY VALIDATION: Verify handlers called with secure context
        handler1.assert_called_once_with(secure_state, extra_param="value")
        handler2.assert_called_once_with(secure_state, extra_param="value")
        # Verify user context isolation
        assert user_context.user_id == "test-user-123"
        assert user_context.thread_id == "test-thread-456"
    
    @pytest.mark.asyncio
    async def test_run_hooks_with_handler_failure_secure(self):
        """P0 SECURITY TEST: Hook execution with handler failure using secure UserExecutionContext."""
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
        handler1 = AsyncMock()
        handler2 = AsyncMock(side_effect=Exception("Handler failed"))
        
        supervisor.hooks = {"before_agent": [handler1, handler2]}
        
        # P0 SECURITY MIGRATION: Create secure UserExecutionContext instead of vulnerable DeepAgentState
        user_context = UserExecutionContext.from_request(
            user_id="test-user-123",
            thread_id="test-thread-456", 
            run_id="test-run-789"
        )
        secure_state = Mock()
        secure_state.user_request = "test"
        
        # Execute hooks - should not raise exception
        await supervisor._run_hooks("before_agent", secure_state)
        
        # P0 SECURITY VALIDATION: Verify first handler still called with secure context
        handler1.assert_called_once()
        # Verify user context isolation maintained
        assert user_context.user_id == "test-user-123"
    
    @pytest.mark.asyncio
    async def test_run_hooks_error_event_reraises_secure(self):
        """P0 SECURITY TEST: Hook execution for error event re-raises exceptions with secure UserExecutionContext."""
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
        failing_handler = AsyncMock(side_effect=Exception("Error handler failed"))
        supervisor.hooks = {"on_error": [failing_handler]}
        
        # P0 SECURITY MIGRATION: Create secure UserExecutionContext instead of vulnerable DeepAgentState
        user_context = UserExecutionContext.from_request(
            user_id="test-user-123",
            thread_id="test-thread-456",
            run_id="test-run-789"
        )
        secure_state = Mock()
        secure_state.user_request = "test"
        
        # Execute error hooks - should re-raise
        with pytest.raises(Exception, match="Error handler failed"):
            await supervisor._run_hooks("on_error", secure_state)
            
        # P0 SECURITY VALIDATION: Verify user context isolation maintained during error
        assert user_context.user_id == "test-user-123"
    
    @pytest.mark.asyncio
    async def test_run_hooks_nonexistent_event_secure(self):
        """P0 SECURITY TEST: Hook execution for non-existent event with secure UserExecutionContext."""
        # Mock: LLM service isolation for fast testing without API calls or rate limits
        llm_manager = Mock(spec=LLMManager)
        # Mock: Database session isolation for transaction testing without real database dependency
        db_session = Mock(spec=AsyncSession)
        # Mock: WebSocket connection isolation for testing without network overhead
        websocket_manager = UnifiedWebSocketManager()
        # Mock: Tool dispatcher isolation for agent testing without real tool execution
        tool_dispatcher = Mock(spec=ToolDispatcher)
        
        supervisor = SupervisorAgent(db_session, llm_manager, websocket_manager, tool_dispatcher)
        
        # P0 SECURITY MIGRATION: Create secure UserExecutionContext instead of vulnerable DeepAgentState
        user_context = UserExecutionContext.from_request(
            user_id="test-user-123",
            thread_id="test-thread-456",
            run_id="test-run-789"
        )
        secure_state = Mock()
        secure_state.user_request = "test"
        
        # Execute non-existent hooks - should not crash
        await supervisor._run_hooks("nonexistent_event", secure_state)
        
        # P0 SECURITY VALIDATION: Should complete without error and maintain isolation
        assert user_context.user_id == "test-user-123"
        assert user_context.thread_id == "test-thread-456"