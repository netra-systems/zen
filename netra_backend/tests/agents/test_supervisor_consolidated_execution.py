"""Execution tests for SupervisorAgent - execution methods and hook management."""

from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch

# Add project root to path
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Add project root to path

from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from sqlalchemy.ext.asyncio import AsyncSession

# Add project root to path


class TestSupervisorAgentExecution:
    """Test execution methods."""
    
    async def test_execute_method(self):
        """Test execute method (BaseSubAgent compatibility)."""
        llm_manager = Mock(spec=LLMManager)
        db_session = Mock(spec=AsyncSession)
        websocket_manager = Mock()
        tool_dispatcher = Mock(spec=ToolDispatcher)
        
        supervisor = SupervisorAgent(db_session, llm_manager, websocket_manager, tool_dispatcher)
        
        # Mock run method
        mock_state = DeepAgentState(user_request="test")
        supervisor.run = AsyncMock(return_value=mock_state)
        
        # Create input state
        state = DeepAgentState(
            user_request="test query",
            chat_thread_id="thread-123",
            user_id="user-456"
        )
        run_id = "run-789"
        
        # Execute
        await supervisor.execute(state, run_id, stream_updates=True)
        
        # Verify run was called with correct parameters
        supervisor.run.assert_called_once_with(
            "test query", "thread-123", "user-456", "run-789"
        )
    
    async def test_execute_method_with_defaults(self):
        """Test execute method with default values."""
        llm_manager = Mock(spec=LLMManager)
        db_session = Mock(spec=AsyncSession)
        websocket_manager = Mock()
        tool_dispatcher = Mock(spec=ToolDispatcher)
        
        supervisor = SupervisorAgent(db_session, llm_manager, websocket_manager, tool_dispatcher)
        
        # Mock run method
        supervisor.run = AsyncMock(return_value=DeepAgentState(user_request="test"))
        
        # Create minimal state
        state = DeepAgentState(user_request="test query")
        run_id = "run-789"
        
        # Execute
        await supervisor.execute(state, run_id, stream_updates=True)
        
        # Verify run was called with defaults
        supervisor.run.assert_called_once_with(
            "test query", "run-789", "default_user", "run-789"
        )
    
    def test_create_run_context(self):
        """Test _create_run_context method."""
        llm_manager = Mock(spec=LLMManager)
        db_session = Mock(spec=AsyncSession)
        websocket_manager = Mock()
        tool_dispatcher = Mock(spec=ToolDispatcher)
        
        supervisor = SupervisorAgent(db_session, llm_manager, websocket_manager, tool_dispatcher)
        
        # Create context
        context = supervisor._create_run_context("thread-123", "user-456", "run-789")
        
        # Verify context structure
        assert context["thread_id"] == "thread-123"
        assert context["user_id"] == "user-456"
        assert context["run_id"] == "run-789"
    
    async def test_run_method_with_execution_lock(self):
        """Test run method uses execution lock."""
        llm_manager = Mock(spec=LLMManager)
        db_session = Mock(spec=AsyncSession)
        websocket_manager = Mock()
        tool_dispatcher = Mock(spec=ToolDispatcher)
        
        supervisor = SupervisorAgent(db_session, llm_manager, websocket_manager, tool_dispatcher)
        
        # Mock components
        supervisor.state_manager.initialize_state = AsyncMock(
            return_value=DeepAgentState(user_request="test")
        )
        supervisor.pipeline_builder.get_execution_pipeline = Mock(return_value=[])
        supervisor._execute_with_context = AsyncMock()
        
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
    
    async def test_execute_with_context(self):
        """Test _execute_with_context method."""
        llm_manager = Mock(spec=LLMManager)
        db_session = Mock(spec=AsyncSession)
        websocket_manager = Mock()
        tool_dispatcher = Mock(spec=ToolDispatcher)
        
        supervisor = SupervisorAgent(db_session, llm_manager, websocket_manager, tool_dispatcher)
        
        # Mock pipeline executor
        supervisor.pipeline_executor.execute_pipeline = AsyncMock()
        supervisor.pipeline_executor.finalize_state = AsyncMock()
        
        # Test data
        pipeline = []
        state = DeepAgentState(user_request="test")
        context = {"run_id": "test-run", "thread_id": "thread-1", "user_id": "user-1"}
        
        # Execute
        await supervisor._execute_with_context(pipeline, state, context)
        
        # Verify pipeline executor calls
        supervisor.pipeline_executor.execute_pipeline.assert_called_once_with(
            pipeline, state, "test-run", context
        )
        supervisor.pipeline_executor.finalize_state.assert_called_once_with(state, context)
    
    async def test_execute_with_state_merge(self):
        """Test execute method properly merges state results."""
        llm_manager = Mock(spec=LLMManager)
        db_session = Mock(spec=AsyncSession)
        websocket_manager = Mock()
        tool_dispatcher = Mock(spec=ToolDispatcher)
        
        supervisor = SupervisorAgent(db_session, llm_manager, websocket_manager, tool_dispatcher)
        
        # Create updated state from run
        updated_state = DeepAgentState(
            user_request="updated query",
            triage_result={"category": "optimization"}
        )
        supervisor.run = AsyncMock(return_value=updated_state)
        
        # Create original state
        original_state = DeepAgentState(user_request="original query")
        
        # Patch the merge_from method at the class level
        with patch.object(DeepAgentState, 'merge_from') as mock_merge:
            # Execute
            await supervisor.execute(original_state, "run-123", stream_updates=True)
            
            # Verify merge was attempted
            mock_merge.assert_called_once_with(updated_state)
    
    async def test_run_method_component_interaction(self):
        """Test run method properly coordinates all components."""
        llm_manager = Mock(spec=LLMManager)
        db_session = Mock(spec=AsyncSession)
        websocket_manager = Mock()
        tool_dispatcher = Mock(spec=ToolDispatcher)
        
        supervisor = SupervisorAgent(db_session, llm_manager, websocket_manager, tool_dispatcher)
        
        # Mock all components
        mock_state = DeepAgentState(user_request="test query")
        mock_pipeline = [Mock()]
        
        supervisor.state_manager.initialize_state = AsyncMock(return_value=mock_state)
        supervisor.pipeline_builder.get_execution_pipeline = Mock(return_value=mock_pipeline)
        supervisor._execute_with_context = AsyncMock()
        
        # Execute
        result = await supervisor.run("test query", "thread-123", "user-456", "run-789")
        
        # Verify component interactions
        supervisor.state_manager.initialize_state.assert_called_once_with(
            "test query", "thread-123", "user-456"
        )
        supervisor.pipeline_builder.get_execution_pipeline.assert_called_once_with(
            "test query", mock_state
        )
        supervisor._execute_with_context.assert_called_once()
        
        # Verify result
        assert result == mock_state


class TestSupervisorAgentHooks:
    """Test hook execution."""
    
    async def test_run_hooks_success(self):
        """Test successful hook execution."""
        llm_manager = Mock(spec=LLMManager)
        db_session = Mock(spec=AsyncSession)
        websocket_manager = Mock()
        tool_dispatcher = Mock(spec=ToolDispatcher)
        
        supervisor = SupervisorAgent(db_session, llm_manager, websocket_manager, tool_dispatcher)
        
        # Create mock handlers
        handler1 = AsyncMock()
        handler2 = AsyncMock()
        
        # Register handlers
        supervisor.hooks["before_agent"] = [handler1, handler2]
        
        # Create state
        state = DeepAgentState(user_request="test")
        
        # Execute hooks
        await supervisor._run_hooks("before_agent", state, extra_param="value")
        
        # Verify handlers called
        handler1.assert_called_once_with(state, extra_param="value")
        handler2.assert_called_once_with(state, extra_param="value")
    
    async def test_run_hooks_with_handler_failure(self):
        """Test hook execution with handler failure."""
        llm_manager = Mock(spec=LLMManager)
        db_session = Mock(spec=AsyncSession)
        websocket_manager = Mock()
        tool_dispatcher = Mock(spec=ToolDispatcher)
        
        supervisor = SupervisorAgent(db_session, llm_manager, websocket_manager, tool_dispatcher)
        
        # Create handlers - one fails
        handler1 = AsyncMock()
        handler2 = AsyncMock(side_effect=Exception("Handler failed"))
        
        supervisor.hooks["before_agent"] = [handler1, handler2]
        
        state = DeepAgentState(user_request="test")
        
        # Execute hooks - should not raise exception
        await supervisor._run_hooks("before_agent", state)
        
        # Verify first handler still called
        handler1.assert_called_once()
    
    async def test_run_hooks_error_event_reraises(self):
        """Test hook execution for error event re-raises exceptions."""
        llm_manager = Mock(spec=LLMManager)
        db_session = Mock(spec=AsyncSession)
        websocket_manager = Mock()
        tool_dispatcher = Mock(spec=ToolDispatcher)
        
        supervisor = SupervisorAgent(db_session, llm_manager, websocket_manager, tool_dispatcher)
        
        # Create failing handler for error event
        failing_handler = AsyncMock(side_effect=Exception("Error handler failed"))
        supervisor.hooks["on_error"] = [failing_handler]
        
        state = DeepAgentState(user_request="test")
        
        # Execute error hooks - should re-raise
        with pytest.raises(Exception, match="Error handler failed"):
            await supervisor._run_hooks("on_error", state)
    
    async def test_run_hooks_nonexistent_event(self):
        """Test hook execution for non-existent event."""
        llm_manager = Mock(spec=LLMManager)
        db_session = Mock(spec=AsyncSession)
        websocket_manager = Mock()
        tool_dispatcher = Mock(spec=ToolDispatcher)
        
        supervisor = SupervisorAgent(db_session, llm_manager, websocket_manager, tool_dispatcher)
        
        state = DeepAgentState(user_request="test")
        
        # Execute non-existent hooks - should not crash
        await supervisor._run_hooks("nonexistent_event", state)
        
        # Should complete without error
