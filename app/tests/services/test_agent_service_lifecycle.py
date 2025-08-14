"""
Agent lifecycle management tests.

Tests agent creation, assignment, state transitions, pool management,
and concurrent execution limits.
"""

import pytest
import asyncio
from unittest.mock import MagicMock

from app.core.exceptions_base import NetraException
from app.tests.helpers.test_agent_orchestration_fixtures import AgentState
from app.tests.helpers.test_agent_orchestration_pytest_fixtures import orchestrator
from app.tests.helpers.test_agent_orchestration_assertions import (
    assert_agent_assignment_correct, assert_agent_pool_size,
    assert_agent_state_correct, assert_orchestration_metrics_valid,
    assert_success_rate_calculation, assert_concurrent_peak_tracked,
    assert_execution_time_positive, assert_failure_metrics_updated,
    setup_orchestrator_limits, setup_failing_agent,
    verify_cleanup_completed
)


class TestAgentLifecycleManagement:
    """Test agent lifecycle management."""
    
    @pytest.mark.asyncio
    async def test_agent_creation_and_assignment(self, orchestrator):
        """Test agent creation and user assignment."""
        agent = await orchestrator.get_or_create_agent("user1")
        
        assert agent is not None
        assert_agent_assignment_correct(agent, "user1")
        assert_agent_pool_size(orchestrator, 0, 1)
        assert orchestrator.orchestration_metrics['agents_created'] == 1
    
    @pytest.mark.asyncio
    async def test_agent_reuse_for_same_user(self, orchestrator):
        """Test agent reuse for same user."""
        agent1 = await orchestrator.get_or_create_agent("user1")
        agent2 = await orchestrator.get_or_create_agent("user1")
        
        assert agent1 is agent2
        assert_agent_pool_size(orchestrator, 0, 1)
    
    @pytest.mark.asyncio
    async def test_agent_pool_management(self, orchestrator):
        """Test agent pool management."""
        agent = await orchestrator.get_or_create_agent("user1")
        await orchestrator.release_agent("user1")
        
        assert_agent_pool_size(orchestrator, 1, 0)
        
        agent2 = await orchestrator.get_or_create_agent("user2")
        assert agent2 is agent
        assert_agent_assignment_correct(agent2, "user2")
        assert_agent_pool_size(orchestrator, 0, 1)
    
    @pytest.mark.asyncio
    async def test_concurrent_agent_limit_enforcement(self, orchestrator):
        """Test enforcement of concurrent agent limits."""
        setup_orchestrator_limits(orchestrator, 3)
        
        agents = []
        for i in range(3):
            agent = await orchestrator.get_or_create_agent(f"user_{i}")
            agents.append(agent)
        
        assert_agent_pool_size(orchestrator, 0, 3)
        
        with pytest.raises(NetraException) as exc_info:
            await orchestrator.get_or_create_agent("user_overflow")
        
        assert "Maximum concurrent agents reached" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_agent_task_execution_tracking(self, orchestrator):
        """Test agent task execution tracking."""
        result = await orchestrator.execute_agent_task(
            "user1", "test request", "run_123", True
        )
        
        assert result['status'] == 'completed'
        assert result['run_id'] == "run_123"
        
        metrics = orchestrator.get_orchestration_metrics()
        assert_orchestration_metrics_valid(metrics, 1)
        assert_success_rate_calculation(metrics, 100.0)
        assert_execution_time_positive(metrics)
    
    @pytest.mark.asyncio
    async def test_agent_task_failure_handling(self, orchestrator):
        """Test agent task failure handling."""
        agent = await orchestrator.get_or_create_agent("user1")
        setup_failing_agent(agent)
        
        with pytest.raises(NetraException):
            await orchestrator.execute_agent_task("user1", "failing request", "run_fail")
        
        metrics = orchestrator.get_orchestration_metrics()
        assert_failure_metrics_updated(metrics, 1)
        assert_success_rate_calculation(metrics, 0.0)
    
    @pytest.mark.asyncio
    async def test_concurrent_agent_orchestration(self, orchestrator):
        """Test concurrent agent orchestration."""
        num_tasks = 5
        tasks = []
        
        for i in range(num_tasks):
            task = orchestrator.execute_agent_task(
                f"user_{i}", f"concurrent request {i}", f"run_{i}"
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        assert len(results) == num_tasks
        assert all(result['status'] == 'completed' for result in results)
        
        metrics = orchestrator.get_orchestration_metrics()
        assert_orchestration_metrics_valid(metrics, num_tasks)
        assert_concurrent_peak_tracked(metrics, num_tasks)
    
    @pytest.mark.asyncio
    async def test_agent_state_transitions(self, orchestrator):
        """Test agent state transitions during lifecycle."""
        agent = await orchestrator.get_or_create_agent("user1")
        
        assert_agent_state_correct(agent, AgentState.IDLE)
        
        task = asyncio.create_task(
            agent.run("test request", "run_state", False)
        )
        
        await asyncio.sleep(0.02)
        assert_agent_state_correct(agent, AgentState.RUNNING)
        
        await task
        assert_agent_state_correct(agent, AgentState.IDLE)
    
    def test_orchestration_metrics_calculation(self, orchestrator):
        """Test orchestration metrics calculation."""
        self._simulate_orchestration_activity(orchestrator)
        
        metrics = orchestrator.get_orchestration_metrics()
        
        assert metrics['total_executions'] == 10
        assert metrics['failed_executions'] == 2
        assert_success_rate_calculation(metrics, 80.0)
        assert metrics['active_agents'] == 2
        assert metrics['pooled_agents'] == 2
        assert metrics['concurrent_peak'] == 3
    
    def _simulate_orchestration_activity(self, orchestrator):
        """Simulate orchestration activity for testing."""
        orchestrator.orchestration_metrics.update({
            'total_executions': 10,
            'failed_executions': 2,
            'agents_created': 5,
            'agents_destroyed': 2,
            'average_execution_time': 0.25,
            'concurrent_peak': 3
        })
        orchestrator.active_agents = 2
        orchestrator.agent_pool = [MagicMock(), MagicMock()]