"""
Test fixtures for agent orchestration tests.

Provides reusable test fixtures for agent service orchestration testing,
including mock agents, orchestrators, and service configurations.
"""

import sys
from pathlib import Path
from test_framework.database.test_database_manager import DatabaseTestManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

# Test framework import - using pytest fixtures instead

import asyncio
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from netra_backend.app.core.exceptions_base import NetraException

from netra_backend.app.services.agent_service import AgentService
from netra_backend.app.services.message_handlers import MessageHandlerService
from netra_backend.app.services.thread_service import ThreadService
from netra_backend.app.services.user_execution_context import UserExecutionContext

class AgentState(Enum):
    IDLE = "idle"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"
    TERMINATED = "terminated"

class MockSupervisorAgent:
    """Mock supervisor agent for testing."""
    
    def __init__(self):
        self.state = AgentState.IDLE
        self.user_id = None
        self.thread_id = None
        self.db_session = None
        self.run_history = []
        self.execution_time = 0.1
        self.should_fail = False
        self.failure_message = "Mock agent failure"
        
    async def run(self, user_request: str, run_id: str, stream_updates: bool = False):
        """Mock agent run method."""
        self.state = AgentState.STARTING
        await self._simulate_startup()
        return await self._execute_run(user_request, run_id, stream_updates)
    
    async def _simulate_startup(self):
        """Simulate agent startup time."""
        await asyncio.sleep(0.01)
        self.state = AgentState.RUNNING
    
    async def _execute_run(self, user_request: str, run_id: str, stream_updates: bool):
        """Execute the mock run with error handling."""
        try:
            if self.should_fail:
                self.state = AgentState.ERROR
                raise NetraException(self.failure_message)
            
            await asyncio.sleep(self.execution_time)
            result = self._create_run_result(user_request, run_id)
            self._record_run(user_request, run_id, stream_updates)
            self.state = AgentState.IDLE
            return result
            
        except Exception as e:
            self.state = AgentState.ERROR
            raise
    
    def _create_run_result(self, user_request: str, run_id: str):
        """Create mock run result."""
        return {
            'status': 'completed',
            'response': f'Processed: {user_request}',
            'run_id': run_id,
            'execution_time': self.execution_time
        }
    
    def _record_run(self, user_request: str, run_id: str, stream_updates: bool):
        """Record run in history."""
        run_record = {
            'user_request': user_request,
            'run_id': run_id,
            'stream_updates': stream_updates,
            'timestamp': datetime.now(UTC),
            'user_id': self.user_id,
            'thread_id': self.thread_id
        }
        self.run_history.append(run_record)
    
    def stop(self):
        """Stop the agent."""
        if self.state == AgentState.RUNNING:
            self.state = AgentState.STOPPING
            asyncio.create_task(self._complete_stop())
    
    async def _complete_stop(self):
        """Complete agent stop."""
        await asyncio.sleep(0.01)
        self.state = AgentState.TERMINATED

class AgentOrchestrator:
    """Orchestrates multiple agents for testing."""
    
    def __init__(self):
        self.agents = {}
        self.agent_pool = []
        self.max_concurrent_agents = 10
        self.active_agents = 0
        self.orchestration_metrics = self._init_metrics()
        
    def _init_metrics(self):
        """Initialize orchestration metrics."""
        return {
            'agents_created': 0,
            'agents_destroyed': 0,
            'total_executions': 0,
            'failed_executions': 0,
            'average_execution_time': 0,
            'concurrent_peak': 0
        }
        
    async def get_or_create_agent(self, user_id: str) -> MockSupervisorAgent:
        """Get existing agent or create new one."""
        if user_id in self.agents:
            return self.agents[user_id]
        
        agent = self._create_or_reuse_agent(user_id)
        self._track_agent_creation()
        return agent
    
    def _create_or_reuse_agent(self, user_id: str) -> MockSupervisorAgent:
        """Create new agent or reuse from pool."""
        if self.active_agents >= self.max_concurrent_agents:
            raise NetraException("Maximum concurrent agents reached")
        
        agent = self._get_agent_from_pool() or self._create_new_agent()
        self._assign_agent_to_user(agent, user_id)
        return agent
    
    def _get_agent_from_pool(self) -> Optional[MockSupervisorAgent]:
        """Get agent from pool if available."""
        return self.agent_pool.pop() if self.agent_pool else None
    
    def _create_new_agent(self) -> MockSupervisorAgent:
        """Create new agent instance."""
        self.orchestration_metrics['agents_created'] += 1
        return MockSupervisorAgent()
    
    def _assign_agent_to_user(self, agent: MockSupervisorAgent, user_id: str):
        """Assign agent to user."""
        agent.user_id = user_id
        self.agents[user_id] = agent
        self.active_agents += 1
        self._update_concurrent_peak()
    
    def _track_agent_creation(self):
        """Track agent creation metrics."""
        if self.active_agents > self.orchestration_metrics['concurrent_peak']:
            self.orchestration_metrics['concurrent_peak'] = self.active_agents
    
    def _update_concurrent_peak(self):
        """Update concurrent peak metric."""
        if self.active_agents > self.orchestration_metrics['concurrent_peak']:
            self.orchestration_metrics['concurrent_peak'] = self.active_agents
    
    async def release_agent(self, user_id: str):
        """Release agent back to pool."""
        if user_id not in self.agents:
            return
            
        agent = self.agents[user_id]
        self._reset_agent(agent)
        self._return_agent_to_pool_or_destroy(agent)
        del self.agents[user_id]
        self.active_agents -= 1
    
    def _reset_agent(self, agent: MockSupervisorAgent):
        """Reset agent state."""
        agent.user_id = None
        agent.thread_id = None
        agent.db_session = None
        agent.state = AgentState.IDLE
    
    def _return_agent_to_pool_or_destroy(self, agent: MockSupervisorAgent):
        """Return agent to pool or destroy if pool is full."""
        if len(self.agent_pool) < 5:  # Max pool size
            self.agent_pool.append(agent)
        else:
            self.orchestration_metrics['agents_destroyed'] += 1
    
    async def execute_agent_task(self, user_id: str, user_request: str, run_id: str, stream_updates: bool = False):
        """Execute task using orchestrated agent."""
        agent = await self.get_or_create_agent(user_id)
        self.orchestration_metrics['total_executions'] += 1
        
        try:
            result = await self._execute_with_timing(agent, user_request, run_id, stream_updates)
            return result
        except Exception as e:
            self.orchestration_metrics['failed_executions'] += 1
            raise
    
    async def _execute_with_timing(self, agent: MockSupervisorAgent, user_request: str, run_id: str, stream_updates: bool):
        """Execute agent task with timing."""
        start_time = datetime.now(UTC)
        result = await agent.run(user_request, run_id, stream_updates)
        execution_time = (datetime.now(UTC) - start_time).total_seconds()
        self._update_average_execution_time(execution_time)
        return result
    
    def _update_average_execution_time(self, execution_time: float):
        """Update average execution time metric."""
        total_execs = self.orchestration_metrics['total_executions']
        current_avg = self.orchestration_metrics['average_execution_time']
        new_avg = ((current_avg * (total_execs - 1)) + execution_time) / total_execs
        self.orchestration_metrics['average_execution_time'] = new_avg
    
    def get_orchestration_metrics(self) -> Dict[str, Any]:
        """Get orchestration metrics."""
        return self._calculate_metrics()
    
    def _calculate_metrics(self) -> Dict[str, Any]:
        """Calculate comprehensive metrics."""
        base_metrics = self.orchestration_metrics.copy()
        base_metrics.update({
            'active_agents': self.active_agents,
            'pooled_agents': len(self.agent_pool),
            'success_rate': self._calculate_success_rate()
        })
        return base_metrics
    
    def _calculate_success_rate(self) -> float:
        """Calculate success rate percentage."""
        total = self.orchestration_metrics['total_executions']
        failed = self.orchestration_metrics['failed_executions']
        return ((total - failed) / max(total, 1)) * 100

# Pytest fixtures are in test_agent_orchestration_pytest_fixtures.py