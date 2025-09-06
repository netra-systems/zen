"""Advanced tests for SupervisorAgent - statistics, edge cases, and concurrent execution."""

import sys
from pathlib import Path
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import TestDatabaseManager
from netra_backend.app.core.agent_registry import AgentRegistry
from netra_backend.app.core.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

# Test framework import - using pytest fixtures instead

import asyncio

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
        websocket_manager = UnifiedWebSocketManager()
        # Mock: Tool dispatcher isolation for agent testing without real tool execution
        tool_dispatcher = Mock(spec=ToolDispatcher)
        
        supervisor = SupervisorAgent(db_session, llm_manager, websocket_manager, tool_dispatcher)
        
        # Mock registry and engine data
        # Mock: Agent service isolation for testing without LLM agent execution
        supervisor.registry.agents = {"agent1": None  # TODO: Use real service instance, "agent2": None  # TODO: Use real service instance, "agent3": None  # TODO: Use real service instance}
        # Mock: Generic component isolation for controlled unit testing
        supervisor.engine.active_runs = {"run1": None  # TODO: Use real service instance, "run2": None  # TODO: Use real service instance}
        # Mock: Generic component isolation for controlled unit testing
        supervisor.engine.run_history = [None  # TODO: Use real service instance, None  # TODO: Use real service instance, None  # TODO: Use real service instance, None  # TODO: Use real service instance]
        
        # Add some hooks
        # Mock: Generic component isolation for controlled unit testing
        supervisor.hooks["before_agent"] = [None  # TODO: Use real service instance, None  # TODO: Use real service instance]
        # Mock: Generic component isolation for controlled unit testing
        supervisor.hooks["after_agent"] = [None  # TODO: Use real service instance]
        
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
        websocket_manager = UnifiedWebSocketManager()
        # Mock: Tool dispatcher isolation for agent testing without real tool execution
        tool_dispatcher = Mock(spec=ToolDispatcher)
        
        supervisor = SupervisorAgent(db_session, llm_manager, websocket_manager, tool_dispatcher)
        
        # Mock workflow executor with delays to test locking
        async def slow_execute_workflow(flow_id, user_prompt, thread_id, user_id, run_id):
            await asyncio.sleep(0.1)
            await asyncio.sleep(0)
    return DeepAgentState(user_request=user_prompt)
        
        supervisor.workflow_executor.execute_workflow_steps = slow_execute_workflow
        
        # Mock flow logger
        supervisor.flow_logger.generate_flow_id = Mock(side_effect=["flow_1", "flow_2"])
        supervisor.flow_logger.start_flow = start_flow_instance  # Initialize appropriate service
        supervisor.flow_logger.complete_flow = complete_flow_instance  # Initialize appropriate service
        
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
        
        # Verify flow logger was called twice (for both executions)
        assert supervisor.flow_logger.start_flow.call_count == 2
        assert supervisor.flow_logger.complete_flow.call_count == 2

    pass