"""
Agent lifecycle management tests for Agent Service orchestration.

MODULE PURPOSE:
Tests the agent lifecycle management functionality including agent creation,
pool management, task execution tracking, and concurrent agent coordination.
Focuses on multi-agent scenarios and resource management.

TEST CATEGORIES:
- Agent Creation and Assignment: User-specific agent allocation
- Agent Reuse: Pool management and agent recycling
- Concurrent Agent Limits: Resource constraint enforcement
- Task Execution Tracking: Metrics and performance monitoring
- Agent State Transitions: Lifecycle state management

PERFORMANCE REQUIREMENTS:
- Unit tests: < 100ms each
- Concurrent tests: < 1s for multiple parallel operations
- Memory: Efficient agent pool management
"""

import pytest
import asyncio
from datetime import datetime, UTC
from typing import Dict, Any
from unittest.mock import MagicMock

from app.core.exceptions_base import NetraException
from .test_agent_service_fixtures import (
    AgentState,
    MockSupervisorAgent, 
    AgentOrchestrator
)


class TestAgentLifecycleManagement:
    """Test agent lifecycle management functionality."""
    
    @pytest.fixture
    def orchestrator(self):
        """Create agent orchestrator for testing."""
        return AgentOrchestrator()
    
    @pytest.mark.asyncio
    async def test_agent_creation_and_assignment(self, orchestrator):
        """Test agent creation and user assignment."""
        agent = await orchestrator.get_or_create_agent("user1")
        
        self._verify_agent_creation(agent, orchestrator)
    
    def _verify_agent_creation(self, agent, orchestrator):
        """Verify agent was created and assigned correctly."""
        assert agent != None
        assert agent.user_id == "user1"
        assert orchestrator.active_agents == 1
        assert orchestrator.orchestration_metrics['agents_created'] == 1
    
    @pytest.mark.asyncio
    async def test_agent_reuse_for_same_user(self, orchestrator):
        """Test agent reuse for same user."""
        agent1 = await orchestrator.get_or_create_agent("user1")
        agent2 = await orchestrator.get_or_create_agent("user1")
        
        self._verify_agent_reuse(agent1, agent2, orchestrator)
    
    def _verify_agent_reuse(self, agent1, agent2, orchestrator):
        """Verify the same agent instance is reused."""
        assert agent1 is agent2
        assert orchestrator.active_agents == 1  # Still only one active
    
    @pytest.mark.asyncio
    async def test_agent_pool_management(self, orchestrator):
        """Test agent pool management and recycling."""
        agent = await orchestrator.get_or_create_agent("user1")
        await orchestrator.release_agent("user1")
        
        self._verify_agent_pooling(orchestrator)
        
        agent2 = await orchestrator.get_or_create_agent("user2")
        self._verify_agent_reuse_from_pool(agent, agent2, orchestrator)
    
    def _verify_agent_pooling(self, orchestrator):
        """Verify agent was added to pool."""
        assert len(orchestrator.agent_pool) == 1
        assert orchestrator.active_agents == 0
    
    def _verify_agent_reuse_from_pool(self, agent, agent2, orchestrator):
        """Verify agent was reused from pool."""
        assert agent2 is agent
        assert agent2.user_id == "user2"
        assert len(orchestrator.agent_pool) == 0
        assert orchestrator.active_agents == 1
    
    @pytest.mark.asyncio
    async def test_concurrent_agent_limit_enforcement(self, orchestrator):
        """Test enforcement of concurrent agent limits."""
        orchestrator.max_concurrent_agents = 3
        agents = await self._create_agents_up_to_limit(orchestrator, 3)
        
        self._verify_limit_reached(orchestrator)
        await self._verify_limit_enforcement(orchestrator)
    
    async def _create_agents_up_to_limit(self, orchestrator, limit):
        """Create agents up to the specified limit."""
        agents = []
        for i in range(limit):
            agent = await orchestrator.get_or_create_agent(f"user_{i}")
            agents.append(agent)
        return agents
    
    def _verify_limit_reached(self, orchestrator):
        """Verify agent limit was reached."""
        assert orchestrator.active_agents == 3
    
    async def _verify_limit_enforcement(self, orchestrator):
        """Verify limit enforcement prevents new agents."""
        with pytest.raises(NetraException) as exc_info:
            await orchestrator.get_or_create_agent("user_overflow")
        
        assert "Maximum concurrent agents reached" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_agent_task_execution_tracking(self, orchestrator):
        """Test agent task execution tracking and metrics."""
        result = await orchestrator.execute_agent_task(
            "user1", "test request", "run_123", True
        )
        
        self._verify_task_execution_result(result)
        metrics = orchestrator.get_orchestration_metrics()
        self._verify_execution_metrics(metrics)
    
    def _verify_task_execution_result(self, result):
        """Verify task execution result is correct."""
        assert result['status'] == 'completed'
        assert result['run_id'] == "run_123"
    
    def _verify_execution_metrics(self, metrics):
        """Verify execution tracking metrics."""
        assert metrics['total_executions'] == 1
        assert metrics['failed_executions'] == 0
        assert metrics['success_rate'] == 100.0
        assert metrics['average_execution_time'] > 0
    
    @pytest.mark.asyncio
    async def test_agent_task_failure_handling(self, orchestrator):
        """Test agent task failure handling and metrics."""
        await self._setup_failing_agent(orchestrator, "user1")
        
        await self._execute_failing_task(orchestrator)
        
        metrics = orchestrator.get_orchestration_metrics()
        self._verify_failure_metrics(metrics)
    
    async def _setup_failing_agent(self, orchestrator, user_id):
        """Setup agent to fail for testing."""
        agent = await orchestrator.get_or_create_agent(user_id)
        agent.should_fail = True
        return agent
    
    async def _execute_failing_task(self, orchestrator):
        """Execute task that should fail."""
        with pytest.raises(NetraException):
            await orchestrator.execute_agent_task("user1", "failing request", "run_fail")
    
    def _verify_failure_metrics(self, metrics):
        """Verify failure tracking metrics."""
        assert metrics['failed_executions'] == 1
        assert metrics['success_rate'] == 0.0
    
    @pytest.mark.asyncio
    async def test_concurrent_agent_orchestration(self, orchestrator):
        """Test concurrent agent orchestration across multiple users."""
        num_tasks = 5
        tasks = self._create_concurrent_orchestration_tasks(orchestrator, num_tasks)
        
        results = await asyncio.gather(*tasks)
        
        self._verify_concurrent_orchestration_results(results, num_tasks, orchestrator)
    
    def _create_concurrent_orchestration_tasks(self, orchestrator, num_tasks):
        """Create concurrent orchestration tasks."""
        tasks = []
        for i in range(num_tasks):
            task = orchestrator.execute_agent_task(
                f"user_{i}", f"concurrent request {i}", f"run_{i}"
            )
            tasks.append(task)
        return tasks
    
    def _verify_concurrent_orchestration_results(self, results, num_tasks, orchestrator):
        """Verify concurrent orchestration results."""
        assert len(results) == num_tasks
        assert all(result['status'] == 'completed' for result in results)
        
        metrics = orchestrator.get_orchestration_metrics()
        assert metrics['total_executions'] == num_tasks
        assert metrics['failed_executions'] == 0
        assert metrics['concurrent_peak'] == num_tasks
    
    @pytest.mark.asyncio
    async def test_agent_state_transitions(self, orchestrator):
        """Test agent state transitions during lifecycle."""
        agent = await orchestrator.get_or_create_agent("user1")
        
        self._verify_initial_state(agent)
        
        task = asyncio.create_task(
            agent.run("test request", "run_state", "user1", "run_state")
        )
        
        await self._verify_running_state(agent)
        await task
        self._verify_idle_state(agent)
    
    def _verify_initial_state(self, agent):
        """Verify agent initial state is IDLE."""
        assert agent.state == AgentState.IDLE
    
    async def _verify_running_state(self, agent):
        """Verify agent transitions to RUNNING state."""
        await asyncio.sleep(0.02)  # Wait for state change
        assert agent.state == AgentState.RUNNING
    
    def _verify_idle_state(self, agent):
        """Verify agent returns to IDLE state."""
        assert agent.state == AgentState.IDLE
    
    def test_orchestration_metrics_calculation(self, orchestrator):
        """Test orchestration metrics calculation accuracy."""
        self._simulate_orchestration_activity(orchestrator)
        
        metrics = orchestrator.get_orchestration_metrics()
        self._verify_metrics_calculation(metrics)
    
    def _simulate_orchestration_activity(self, orchestrator):
        """Simulate orchestration activity for metrics testing."""
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
    
    def _verify_metrics_calculation(self, metrics):
        """Verify metrics calculation is correct."""
        assert metrics['total_executions'] == 10
        assert metrics['failed_executions'] == 2
        assert metrics['success_rate'] == 80.0  # (10-2)/10 * 100
        assert metrics['active_agents'] == 2
        assert metrics['pooled_agents'] == 2
        assert metrics['concurrent_peak'] == 3