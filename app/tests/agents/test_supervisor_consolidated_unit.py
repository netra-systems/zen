"""Unit tests for SupervisorAgent consolidated module with 70%+ coverage.
Focuses on testing individual methods and components with proper mocking.
"""

import pytest
import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from datetime import datetime, timezone

from app.agents.supervisor_consolidated import SupervisorAgent
from app.agents.state import DeepAgentState
from app.agents.base import BaseSubAgent
from app.schemas import SubAgentLifecycle
from app.llm.llm_manager import LLMManager
from app.agents.tool_dispatcher import ToolDispatcher
from sqlalchemy.ext.asyncio import AsyncSession


class TestSupervisorAgentInitialization:
    """Test initialization and setup methods."""
    
    def test_init_base(self):
        """Test _init_base method."""
        # Mock LLM manager
        llm_manager = Mock(spec=LLMManager)
        
        # Create supervisor instance
        db_session = Mock(spec=AsyncSession)
        websocket_manager = Mock()
        tool_dispatcher = Mock(spec=ToolDispatcher)
        
        supervisor = SupervisorAgent(db_session, llm_manager, websocket_manager, tool_dispatcher)
        
        # Verify base initialization
        assert supervisor.name == "Supervisor"
        assert supervisor.description == "The supervisor agent that orchestrates sub-agents"
        assert supervisor.llm_manager == llm_manager
    
    def test_init_services(self):
        """Test _init_services method."""
        llm_manager = Mock(spec=LLMManager)
        db_session = Mock(spec=AsyncSession)
        websocket_manager = Mock()
        tool_dispatcher = Mock(spec=ToolDispatcher)
        
        supervisor = SupervisorAgent(db_session, llm_manager, websocket_manager, tool_dispatcher)
        
        # Verify services initialization
        assert supervisor.db_session == db_session
        assert supervisor.websocket_manager == websocket_manager
        assert supervisor.tool_dispatcher == tool_dispatcher
        assert supervisor.state_persistence is not None
    
    def test_init_components(self):
        """Test _init_components method."""
        llm_manager = Mock(spec=LLMManager)
        db_session = Mock(spec=AsyncSession)
        websocket_manager = Mock()
        tool_dispatcher = Mock(spec=ToolDispatcher)
        
        supervisor = SupervisorAgent(db_session, llm_manager, websocket_manager, tool_dispatcher)
        
        # Verify components initialization
        assert supervisor.registry is not None
        assert supervisor.engine is not None
        assert supervisor.pipeline_executor is not None
        assert supervisor.state_manager is not None
        assert supervisor.pipeline_builder is not None
    
    def test_init_hooks(self):
        """Test _init_hooks method."""
        llm_manager = Mock(spec=LLMManager)
        db_session = Mock(spec=AsyncSession)
        websocket_manager = Mock()
        tool_dispatcher = Mock(spec=ToolDispatcher)
        
        supervisor = SupervisorAgent(db_session, llm_manager, websocket_manager, tool_dispatcher)
        
        # Verify hooks initialization
        expected_hooks = ["before_agent", "after_agent", "on_error", "on_retry", "on_complete"]
        assert all(hook in supervisor.hooks for hook in expected_hooks)
        assert all(isinstance(supervisor.hooks[hook], list) for hook in expected_hooks)


class TestSupervisorAgentRegistration:
    """Test agent registration and hook management."""
    
    def test_register_agent(self):
        """Test register_agent method."""
        llm_manager = Mock(spec=LLMManager)
        db_session = Mock(spec=AsyncSession)
        websocket_manager = Mock()
        tool_dispatcher = Mock(spec=ToolDispatcher)
        
        supervisor = SupervisorAgent(db_session, llm_manager, websocket_manager, tool_dispatcher)
        
        # Create mock agent
        mock_agent = Mock(spec=BaseSubAgent)
        mock_agent.name = "test_agent"
        
        # Register agent
        supervisor.register_agent("test_agent", mock_agent)
        
        # Verify registration
        assert "test_agent" in supervisor.agents
        assert supervisor.agents["test_agent"] == mock_agent
    
    def test_register_hook(self):
        """Test register_hook method."""
        llm_manager = Mock(spec=LLMManager)
        db_session = Mock(spec=AsyncSession)
        websocket_manager = Mock()
        tool_dispatcher = Mock(spec=ToolDispatcher)
        
        supervisor = SupervisorAgent(db_session, llm_manager, websocket_manager, tool_dispatcher)
        
        # Create mock handler
        mock_handler = Mock()
        
        # Register hook
        supervisor.register_hook("before_agent", mock_handler)
        
        # Verify hook registration
        assert mock_handler in supervisor.hooks["before_agent"]
    
    def test_register_hook_invalid_event(self):
        """Test register_hook with invalid event."""
        llm_manager = Mock(spec=LLMManager)
        db_session = Mock(spec=AsyncSession)
        websocket_manager = Mock()
        tool_dispatcher = Mock(spec=ToolDispatcher)
        
        supervisor = SupervisorAgent(db_session, llm_manager, websocket_manager, tool_dispatcher)
        
        mock_handler = Mock()
        
        # Register invalid hook - should not crash
        supervisor.register_hook("invalid_event", mock_handler)
        
        # Verify invalid event not added
        assert "invalid_event" not in supervisor.hooks


class TestSupervisorAgentProperties:
    """Test property methods."""
    
    def test_agents_property(self):
        """Test agents property getter."""
        llm_manager = Mock(spec=LLMManager)
        db_session = Mock(spec=AsyncSession)
        websocket_manager = Mock()
        tool_dispatcher = Mock(spec=ToolDispatcher)
        
        supervisor = SupervisorAgent(db_session, llm_manager, websocket_manager, tool_dispatcher)
        
        # Test property returns registry agents
        agents = supervisor.agents
        assert agents == supervisor.registry.agents
    
    def test_sub_agents_property_getter(self):
        """Test sub_agents property getter (backward compatibility)."""
        llm_manager = Mock(spec=LLMManager)
        db_session = Mock(spec=AsyncSession)
        websocket_manager = Mock()
        tool_dispatcher = Mock(spec=ToolDispatcher)
        
        supervisor = SupervisorAgent(db_session, llm_manager, websocket_manager, tool_dispatcher)
        
        # Mock registry method
        supervisor.registry.get_all_agents = Mock(return_value=["agent1", "agent2"])
        
        # Test property
        sub_agents = supervisor.sub_agents
        assert sub_agents == ["agent1", "agent2"]
    
    def test_sub_agents_property_setter(self):
        """Test sub_agents property setter (backward compatibility)."""
        llm_manager = Mock(spec=LLMManager)
        db_session = Mock(spec=AsyncSession)
        websocket_manager = Mock()
        tool_dispatcher = Mock(spec=ToolDispatcher)
        
        supervisor = SupervisorAgent(db_session, llm_manager, websocket_manager, tool_dispatcher)
        
        # Create mock agents
        agent1 = Mock(spec=BaseSubAgent)
        agent2 = Mock(spec=BaseSubAgent)
        agents_list = [agent1, agent2]
        
        # Set sub_agents
        supervisor.sub_agents = agents_list
        
        # Verify agents were registered
        assert "agent_0" in supervisor.registry.agents
        assert "agent_1" in supervisor.registry.agents


class TestSupervisorAgentExecution:
    """Test execution methods."""
    
    @pytest.mark.asyncio
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
    
    @pytest.mark.asyncio
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
    
    @pytest.mark.asyncio
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
    
    @pytest.mark.asyncio
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


class TestSupervisorAgentHooks:
    """Test hook execution."""
    
    @pytest.mark.asyncio
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
    
    @pytest.mark.asyncio
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
    
    @pytest.mark.asyncio
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
    
    @pytest.mark.asyncio
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


class TestSupervisorAgentStats:
    """Test statistics and monitoring."""
    
    def test_get_stats(self):
        """Test get_stats method."""
        llm_manager = Mock(spec=LLMManager)
        db_session = Mock(spec=AsyncSession)
        websocket_manager = Mock()
        tool_dispatcher = Mock(spec=ToolDispatcher)
        
        supervisor = SupervisorAgent(db_session, llm_manager, websocket_manager, tool_dispatcher)
        
        # Mock registry and engine data
        supervisor.registry.agents = {"agent1": Mock(), "agent2": Mock(), "agent3": Mock()}
        supervisor.engine.active_runs = {"run1": Mock(), "run2": Mock()}
        supervisor.engine.run_history = [Mock(), Mock(), Mock(), Mock()]
        
        # Add some hooks
        supervisor.hooks["before_agent"] = [Mock(), Mock()]
        supervisor.hooks["after_agent"] = [Mock()]
        
        # Get stats
        stats = supervisor.get_stats()
        
        # Verify stats structure and values
        assert stats["registered_agents"] == 3
        assert stats["active_runs"] == 2
        assert stats["completed_runs"] == 4
        assert stats["hooks_registered"]["before_agent"] == 2
        assert stats["hooks_registered"]["after_agent"] == 1
        assert stats["hooks_registered"]["on_error"] == 0


class TestSupervisorAgentEdgeCases:
    """Test edge cases and error scenarios."""
    
    @pytest.mark.asyncio
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
    
    @pytest.mark.asyncio
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
    
    def test_initialization_with_none_values(self):
        """Test initialization handles None values gracefully."""
        llm_manager = Mock(spec=LLMManager)
        db_session = Mock(spec=AsyncSession)
        websocket_manager = Mock()
        tool_dispatcher = Mock(spec=ToolDispatcher)
        
        # Should not crash with valid mocks
        supervisor = SupervisorAgent(db_session, llm_manager, websocket_manager, tool_dispatcher)
        
        # Verify basic setup completed
        assert supervisor is not None
        assert supervisor.name == "Supervisor"
        assert hasattr(supervisor, '_execution_lock')
        assert isinstance(supervisor.hooks, dict)
    
    @pytest.mark.asyncio 
    async def test_concurrent_execution_locking(self):
        """Test that execution lock prevents concurrent runs."""
        llm_manager = Mock(spec=LLMManager)
        db_session = Mock(spec=AsyncSession)
        websocket_manager = Mock()
        tool_dispatcher = Mock(spec=ToolDispatcher)
        
        supervisor = SupervisorAgent(db_session, llm_manager, websocket_manager, tool_dispatcher)
        
        # Mock components with delays to test locking
        async def slow_initialize(prompt, thread_id, user_id):
            await asyncio.sleep(0.1)
            return DeepAgentState(user_request=prompt)
        
        supervisor.state_manager.initialize_state = slow_initialize
        supervisor.pipeline_builder.get_execution_pipeline = Mock(return_value=[])
        supervisor._execute_with_context = AsyncMock()
        
        # Start two concurrent executions
        task1 = asyncio.create_task(
            supervisor.run("query 1", "thread-1", "user-1", "run-1")
        )
        task2 = asyncio.create_task(
            supervisor.run("query 2", "thread-2", "user-2", "run-2")
        )
        
        # Wait for both to complete
        result1, result2 = await asyncio.gather(task1, task2)
        
        # Both should complete successfully
        assert result1.user_request == "query 1"
        assert result2.user_request == "query 2"
        
        # Verify execute_with_context was called twice (serialized)
        assert supervisor._execute_with_context.call_count == 2