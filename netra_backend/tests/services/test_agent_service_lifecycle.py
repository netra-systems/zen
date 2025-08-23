"""
Agent service lifecycle management tests.

MODULE PURPOSE:
Tests agent lifecycle management including creation, assignment, pooling, 
state transitions, and resource cleanup. Focuses on multi-agent coordination
and concurrent execution patterns.

TEST CATEGORIES:
- Agent creation and user assignment
- Agent pooling and reuse
- Concurrent agent limits enforcement  
- Task execution tracking and metrics
- Agent state transitions during execution
- Resource cleanup and pool management

PERFORMANCE REQUIREMENTS:
- Unit tests: < 100ms each
- Concurrent tests: < 1s for multiple parallel operations
"""

import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

import asyncio
from unittest.mock import MagicMock

import pytest

from netra_backend.app.core.exceptions_base import NetraException
from netra_backend.tests.test_agent_service_fixtures import (
    orchestrator,
    verify_orchestration_metrics,
)
from netra_backend.tests.test_agent_service_mock_classes import AgentState

class TestAgentLifecycleManagement:
    """Test agent lifecycle management functionality."""
    async def test_agent_creation_and_assignment(self, orchestrator):
        """Test agent creation and user assignment."""
        agent = await orchestrator.get_or_create_agent("user1")
        
        assert agent != None
        assert agent.user_id == "user1"
        self._verify_agent_creation_metrics(orchestrator)
    
    def _verify_agent_creation_metrics(self, orchestrator):
        """Verify agent creation updates metrics correctly."""
        assert orchestrator.active_agents == 1
        assert orchestrator.orchestration_metrics['agents_created'] == 1
    async def test_agent_reuse_for_same_user(self, orchestrator):
        """Test agent reuse for same user."""
        agent1 = await orchestrator.get_or_create_agent("user1")
        agent2 = await orchestrator.get_or_create_agent("user1")
        
        assert agent1 is agent2
        assert orchestrator.active_agents == 1
    async def test_agent_pool_management(self, orchestrator):
        """Test agent pool management and reuse."""
        agent = await orchestrator.get_or_create_agent("user1")
        await orchestrator.release_agent("user1")
        
        self._verify_agent_pooled(orchestrator)
        agent2 = await orchestrator.get_or_create_agent("user2")
        self._verify_agent_reused_from_pool(orchestrator, agent, agent2)
    
    def _verify_agent_pooled(self, orchestrator):
        """Verify agent was properly pooled."""
        assert len(orchestrator.agent_pool) == 1
        assert orchestrator.active_agents == 0
    
    def _verify_agent_reused_from_pool(self, orchestrator, original_agent, reused_agent):
        """Verify agent was reused from pool correctly."""
        assert reused_agent is original_agent
        assert reused_agent.user_id == "user2"
        assert len(orchestrator.agent_pool) == 0
        assert orchestrator.active_agents == 1
    async def test_concurrent_agent_limit_enforcement(self, orchestrator):
        """Test enforcement of concurrent agent limits."""
        orchestrator.max_concurrent_agents = 3
        
        agents = await self._create_agents_up_to_limit(orchestrator, 3)
        assert orchestrator.active_agents == 3
        
        with pytest.raises(NetraException) as exc_info:
            await orchestrator.get_or_create_agent("user_overflow")
        
        assert "Maximum concurrent agents reached" in str(exc_info.value)
    
    async def _create_agents_up_to_limit(self, orchestrator, limit):
        """Create agents up to the specified limit."""
        agents = []
        for i in range(limit):
            agent = await orchestrator.get_or_create_agent(f"user_{i}")
            agents.append(agent)
        return agents
    async def test_agent_task_execution_tracking(self, orchestrator):
        """Test agent task execution tracking and metrics."""
        result = await orchestrator.execute_agent_task("user1", "test request", "run_123", True)
        
        self._verify_task_execution_result(result)
        metrics = orchestrator.get_orchestration_metrics()
        self._verify_execution_metrics(metrics)
    
    def _verify_task_execution_result(self, result):
        """Verify task execution result structure."""
        assert result['status'] == 'completed'
        assert result['run_id'] == "run_123"
    
    def _verify_execution_metrics(self, metrics):
        """Verify execution tracking metrics."""
        assert metrics['total_executions'] == 1
        assert metrics['failed_executions'] == 0
        assert metrics['success_rate'] == 100.0
        assert metrics['average_execution_time'] > 0
    async def test_agent_task_failure_handling(self, orchestrator):
        """Test agent task failure handling and metrics."""
        agent = await self._setup_failing_agent(orchestrator, "user1")
        
        with pytest.raises(NetraException):
            await orchestrator.execute_agent_task("user1", "failing request", "run_fail")
        
        metrics = orchestrator.get_orchestration_metrics()
        self._verify_failure_metrics(metrics)
    
    async def _setup_failing_agent(self, orchestrator, user_id):
        """Setup agent to fail for testing."""
        agent = await orchestrator.get_or_create_agent(user_id)
        agent.should_fail = True
        return agent
    
    def _verify_failure_metrics(self, metrics):
        """Verify failure tracking metrics."""
        assert metrics['failed_executions'] == 1
        assert metrics['success_rate'] == 0.0
    async def test_concurrent_agent_orchestration(self, orchestrator):
        """Test concurrent agent orchestration with multiple tasks."""
        num_tasks = 5
        tasks = self._create_concurrent_orchestration_tasks(orchestrator, num_tasks)
        
        results = await asyncio.gather(*tasks)
        
        self._verify_concurrent_orchestration_results(results, num_tasks)
        self._verify_concurrent_orchestration_metrics(orchestrator, num_tasks)
    
    def _create_concurrent_orchestration_tasks(self, orchestrator, num_tasks):
        """Create concurrent orchestration tasks."""
        tasks = []
        for i in range(num_tasks):
            task = orchestrator.execute_agent_task(
                f"user_{i}", f"concurrent request {i}", f"run_{i}"
            )
            tasks.append(task)
        return tasks
    
    def _verify_concurrent_orchestration_results(self, results, num_tasks):
        """Verify concurrent orchestration results."""
        assert len(results) == num_tasks
        assert all(result['status'] == 'completed' for result in results)
    
    def _verify_concurrent_orchestration_metrics(self, orchestrator, num_tasks):
        """Verify concurrent orchestration metrics."""
        metrics = orchestrator.get_orchestration_metrics()
        assert metrics['total_executions'] == num_tasks
        assert metrics['failed_executions'] == 0
        assert metrics['concurrent_peak'] == num_tasks
    async def test_agent_state_transitions(self, orchestrator):
        """Test agent state transitions during lifecycle."""
        agent = await orchestrator.get_or_create_agent("user1")
        
        assert agent.state == AgentState.IDLE
        
        task = asyncio.create_task(
            agent.run("test request", "run_state", "user1", "run_state")
        )
        await self._verify_agent_running_state(agent)
        
        await task
        assert agent.state == AgentState.IDLE
    
    async def _verify_agent_running_state(self, agent):
        """Verify agent transitions to running state."""
        await asyncio.sleep(0.02)  # Wait for state change
        assert agent.state == AgentState.RUNNING
    
    def test_orchestration_metrics_calculation(self, orchestrator):
        """Test orchestration metrics calculation."""
        self._setup_orchestrator_metrics(orchestrator)
        
        metrics = orchestrator.get_orchestration_metrics()
        
        self._verify_calculated_metrics(metrics)
    
    def _setup_orchestrator_metrics(self, orchestrator):
        """Setup orchestrator with test metrics data."""
        orchestrator.orchestration_metrics.update({
            'total_executions': 10,
            'failed_executions': 2,
            'agents_created': 5,
            'agents_destroyed': 2,
            'average_execution_time': 0.25,
            'concurrent_peak': 3
        })
        orchestrator.active_agents = 2
        orchestrator.agent_pool = [MagicMock(), MagicMock()]  # 2 in pool
    
    def _verify_calculated_metrics(self, metrics):
        """Verify calculated metrics are correct."""
        assert metrics['total_executions'] == 10
        assert metrics['failed_executions'] == 2
        assert metrics['success_rate'] == 80.0  # (10-2)/10 * 100
        assert metrics['active_agents'] == 2
        assert metrics['pooled_agents'] == 2
        assert metrics['concurrent_peak'] == 3

class TestAgentPoolOptimization:
    """Test agent pool optimization and resource management."""
    async def test_agent_pool_size_limits(self, orchestrator):
        """Test agent pool maintains size limits."""
        agents = []
        for i in range(7):  # Beyond pool limit of 5
            agent = await orchestrator.get_or_create_agent(f"user_{i}")
            agents.append((f"user_{i}", agent))
        for user_id, agent in agents:
            await orchestrator.release_agent(user_id)
        assert len(orchestrator.agent_pool) <= 5
    async def test_agent_state_reset_on_release(self, orchestrator):
        """Test agent state is properly reset when released."""
        agent = await orchestrator.get_or_create_agent("user1")
        agent.thread_id = "test_thread"
        agent.db_session = "test_session"
        
        await orchestrator.release_agent("user1")
        
        self._verify_agent_state_reset(agent)
    
    def _verify_agent_state_reset(self, agent):
        """Verify agent state was properly reset."""
        assert agent.user_id is None
        assert agent.thread_id is None
        assert agent.db_session is None
        assert agent.state == AgentState.IDLE
    async def test_agent_cleanup_on_error(self, orchestrator):
        """Test proper cleanup when agent assignment fails."""
        orchestrator.max_concurrent_agents = 1
        
        # First agent succeeds
        agent1 = await orchestrator.get_or_create_agent("user1")
        initial_active = orchestrator.active_agents
        
        # Second agent should fail
        try:
            await orchestrator.get_or_create_agent("user2")
            assert False, "Should have raised NetraException"
        except NetraException:
            pass
        
        # Active count should remain unchanged
        assert orchestrator.active_agents == initial_active
    async def test_concurrent_pool_access(self, orchestrator):
        """Test concurrent access to agent pool is thread-safe."""
        num_concurrent = 10
        
        # Create tasks that get and release agents concurrently
        tasks = []
        for i in range(num_concurrent):
            task = self._agent_get_release_cycle(orchestrator, f"user_{i}")
            tasks.append(task)
        
        await asyncio.gather(*tasks)
        
        # Pool should be in consistent state
        assert orchestrator.active_agents == 0
        assert len(orchestrator.agent_pool) <= 5  # Pool limit
    
    async def _agent_get_release_cycle(self, orchestrator, user_id):
        """Get agent, use briefly, then release."""
        agent = await orchestrator.get_or_create_agent(user_id)
        await asyncio.sleep(0.01)  # Brief usage
        await orchestrator.release_agent(user_id)