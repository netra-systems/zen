"""Advanced tests for SupervisorAgent - statistics, edge cases, and concurrent execution."""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.agents.state import DeepAgentState

from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.llm.llm_manager import LLMManager

class TestSupervisorAgentStats:
    """Test statistics and monitoring."""
    
    def test_get_stats(self):
        """Test get_stats method."""
        # Mock: LLM service isolation for fast testing without API calls or rate limits
        llm_manager = Mock(spec=LLMManager)
        # Mock: Database session isolation for transaction testing without real database dependency
        db_session = Mock(spec=AsyncSession)
        # Mock: WebSocket connection isolation for testing without network overhead
        websocket_manager = Mock()
        # Mock: Tool dispatcher isolation for agent testing without real tool execution
        tool_dispatcher = Mock(spec=ToolDispatcher)
        
        supervisor = SupervisorAgent(db_session, llm_manager, websocket_manager, tool_dispatcher)
        
        # Mock registry and engine data
        # Mock: Agent service isolation for testing without LLM agent execution
        supervisor.registry.agents = {"agent1": Mock(), "agent2": Mock(), "agent3": Mock()}
        # Mock: Generic component isolation for controlled unit testing
        supervisor.engine.active_runs = {"run1": Mock(), "run2": Mock()}
        # Mock: Generic component isolation for controlled unit testing
        supervisor.engine.run_history = [Mock(), Mock(), Mock(), Mock()]
        
        # Add some hooks
        # Mock: Generic component isolation for controlled unit testing
        supervisor.hooks["before_agent"] = [Mock(), Mock()]
        # Mock: Generic component isolation for controlled unit testing
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
    async def test_concurrent_execution_locking(self):
        """Test that execution lock prevents concurrent runs."""
        # Mock: LLM service isolation for fast testing without API calls or rate limits
        llm_manager = Mock(spec=LLMManager)
        # Mock: Database session isolation for transaction testing without real database dependency
        db_session = Mock(spec=AsyncSession)
        # Mock: WebSocket connection isolation for testing without network overhead
        websocket_manager = Mock()
        # Mock: Tool dispatcher isolation for agent testing without real tool execution
        tool_dispatcher = Mock(spec=ToolDispatcher)
        
        supervisor = SupervisorAgent(db_session, llm_manager, websocket_manager, tool_dispatcher)
        
        # Mock components with delays to test locking
        async def slow_initialize(prompt, thread_id, user_id, run_id):
            await asyncio.sleep(0.1)
            return DeepAgentState(user_request=prompt)
        
        supervisor.state_manager.initialize_state = slow_initialize
        # Mock: Component isolation for controlled unit testing
        supervisor.pipeline_builder.get_execution_pipeline = Mock(return_value=[])
        # Mock: Generic component isolation for controlled unit testing
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
