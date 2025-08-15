"""
Mock classes for agent service testing.

MODULE PURPOSE:
Mock implementations of AgentState, MockSupervisorAgent, and AgentOrchestrator
for testing agent service functionality without external dependencies.

CONTAINS:
- AgentState enumeration
- MockSupervisorAgent with configurable behavior
- AgentOrchestrator for multi-agent testing

COMPLIANCE:
- All functions ≤8 lines
- Module ≤300 lines  
- Single responsibility focus
"""

import asyncio
from datetime import datetime, UTC
from typing import Dict, Any
from enum import Enum

from app.core.exceptions_base import NetraException


class AgentState(Enum):
    """Agent state enumeration for testing."""
    IDLE = "idle"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"
    TERMINATED = "terminated"


class MockSupervisorAgent:
    """Mock supervisor agent for testing without LLM calls."""
    
    def __init__(self):
        self._initialize_state()
        self._initialize_config()
    
    def _initialize_state(self):
        """Initialize agent state properties."""
        self.state = AgentState.IDLE
        self.user_id = None
        self.thread_id = None
        self.db_session = None
        self.run_history = []
    
    def _initialize_config(self):
        """Initialize agent configuration."""
        self.execution_time = 0.1
        self.should_fail = False
        self.failure_message = "Mock agent failure"
    
    async def run(self, user_prompt: str, thread_id: str, user_id: str, run_id: str):
        """Execute mock agent run with configurable behavior."""
        await self._start_execution()
        result = await self._execute_with_error_handling(user_prompt, thread_id, user_id, run_id)
        return result
    
    async def _start_execution(self):
        """Start agent execution with state transition."""
        self.state = AgentState.STARTING
        await asyncio.sleep(0.01)
        self.state = AgentState.RUNNING
    
    async def _execute_with_error_handling(self, user_prompt: str, thread_id: str, user_id: str, run_id: str):
        """Execute task with error handling and recording."""
        try:
            return await self._process_request(user_prompt, thread_id, user_id, run_id)
        except Exception as e:
            self.state = AgentState.ERROR
            raise
    
    async def _process_request(self, user_prompt: str, thread_id: str, user_id: str, run_id: str):
        """Process the actual request with failure simulation."""
        if self.should_fail:
            self.state = AgentState.ERROR
            raise NetraException(self.failure_message)
        
        await asyncio.sleep(self.execution_time)
        self._record_execution(user_prompt, thread_id, user_id, run_id)
        return self._create_success_response(user_prompt, run_id)
    
    def _record_execution(self, user_prompt: str, thread_id: str, user_id: str, run_id: str):
        """Record execution details for verification."""
        run_record = {
            'user_prompt': user_prompt,
            'thread_id': thread_id,
            'user_id': user_id,
            'run_id': run_id,
            'timestamp': datetime.now(UTC)
        }
        self.run_history.append(run_record)
    
    def _create_success_response(self, user_prompt: str, run_id: str):
        """Create successful execution response."""
        self.state = AgentState.IDLE
        return {
            'status': 'completed',
            'response': f'Processed: {user_prompt}',
            'run_id': run_id,
            'execution_time': self.execution_time
        }
    
    def stop(self):
        """Stop the agent with state transition."""
        if self.state == AgentState.RUNNING:
            self.state = AgentState.STOPPING
            asyncio.create_task(self._complete_stop())
    
    async def _complete_stop(self):
        """Complete agent stop operation."""
        await asyncio.sleep(0.01)
        self.state = AgentState.TERMINATED


class AgentOrchestrator:
    """Test orchestrator for managing multiple mock agents."""
    
    def __init__(self):
        self._initialize_pools()
        self._initialize_limits()
        self._initialize_metrics()
    
    def _initialize_pools(self):
        """Initialize agent pools and tracking."""
        self.agents = {}
        self.agent_pool = []
        self.active_agents = 0
    
    def _initialize_limits(self):
        """Initialize concurrency limits."""
        self.max_concurrent_agents = 10
    
    def _initialize_metrics(self):
        """Initialize orchestration metrics."""
        self.orchestration_metrics = {
            'agents_created': 0,
            'agents_destroyed': 0,
            'total_executions': 0,
            'failed_executions': 0,
            'average_execution_time': 0,
            'concurrent_peak': 0
        }
    
    async def get_or_create_agent(self, user_id: str) -> MockSupervisorAgent:
        """Get existing agent or create new one for user."""
        if user_id in self.agents:
            return self.agents[user_id]
        
        agent = await self._create_new_agent(user_id)
        return agent
    
    async def _create_new_agent(self, user_id: str) -> MockSupervisorAgent:
        """Create new agent with concurrency checks."""
        if self.active_agents >= self.max_concurrent_agents:
            raise NetraException("Maximum concurrent agents reached")
        
        agent = self._get_agent_from_pool_or_create()
        self._assign_agent_to_user(agent, user_id)
        return agent
    
    def _get_agent_from_pool_or_create(self) -> MockSupervisorAgent:
        """Get agent from pool or create new one."""
        if self.agent_pool:
            return self.agent_pool.pop()
        
        self.orchestration_metrics['agents_created'] += 1
        return MockSupervisorAgent()
    
    def _assign_agent_to_user(self, agent: MockSupervisorAgent, user_id: str):
        """Assign agent to user and update tracking."""
        agent.user_id = user_id
        self.agents[user_id] = agent
        self.active_agents += 1
        self._update_concurrent_peak()
    
    def _update_concurrent_peak(self):
        """Update peak concurrent agents metric."""
        if self.active_agents > self.orchestration_metrics['concurrent_peak']:
            self.orchestration_metrics['concurrent_peak'] = self.active_agents
    
    async def release_agent(self, user_id: str):
        """Release agent back to pool with cleanup."""
        if user_id not in self.agents:
            return
        
        agent = self.agents[user_id]
        self._reset_agent_state(agent)
        self._return_agent_to_pool_or_destroy(agent)
        self._cleanup_user_assignment(user_id)
    
    def _reset_agent_state(self, agent: MockSupervisorAgent):
        """Reset agent state for reuse."""
        agent.user_id = None
        agent.thread_id = None
        agent.db_session = None
        agent.state = AgentState.IDLE
    
    def _return_agent_to_pool_or_destroy(self, agent: MockSupervisorAgent):
        """Return agent to pool or destroy if pool full."""
        if len(self.agent_pool) < 5:
            self.agent_pool.append(agent)
        else:
            self.orchestration_metrics['agents_destroyed'] += 1
    
    def _cleanup_user_assignment(self, user_id: str):
        """Clean up user-agent assignment."""
        del self.agents[user_id]
        self.active_agents -= 1
    
    async def execute_agent_task(self, user_id: str, user_request: str, run_id: str, thread_id: str = None):
        """Execute task using orchestrated agent."""
        agent = await self.get_or_create_agent(user_id)
        self.orchestration_metrics['total_executions'] += 1
        
        try:
            result = await self._execute_task_with_timing(agent, user_request, thread_id, user_id, run_id)
            return result
        except Exception as e:
            self.orchestration_metrics['failed_executions'] += 1
            raise
    
    async def _execute_task_with_timing(self, agent: MockSupervisorAgent, user_request: str, thread_id: str, user_id: str, run_id: str):
        """Execute task with execution time tracking."""
        start_time = datetime.now(UTC)
        result = await agent.run(user_request, thread_id or run_id, user_id, run_id)
        execution_time = (datetime.now(UTC) - start_time).total_seconds()
        self._update_average_execution_time(execution_time)
        return result
    
    def _update_average_execution_time(self, execution_time: float):
        """Update rolling average execution time."""
        total_execs = self.orchestration_metrics['total_executions']
        current_avg = self.orchestration_metrics['average_execution_time']
        new_avg = ((current_avg * (total_execs - 1)) + execution_time) / total_execs
        self.orchestration_metrics['average_execution_time'] = new_avg
    
    def get_orchestration_metrics(self) -> Dict[str, Any]:
        """Get comprehensive orchestration metrics."""
        return {
            **self.orchestration_metrics,
            'active_agents': self.active_agents,
            'pooled_agents': len(self.agent_pool),
            'success_rate': self._calculate_success_rate()
        }
    
    def _calculate_success_rate(self) -> float:
        """Calculate success rate percentage."""
        total = self.orchestration_metrics['total_executions']
        failed = self.orchestration_metrics['failed_executions']
        if total == 0:
            return 100.0
        return ((total - failed) / total) * 100