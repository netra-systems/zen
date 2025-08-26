"""Mock classes for agent service testing.

This module provides mock classes and enums for testing agent services.
"""

import asyncio
from enum import Enum
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from typing import Dict, Any, Optional


class AgentState(Enum):
    """Mock agent state enum."""
    IDLE = "idle"
    ACTIVE = "active"
    RUNNING = "running"
    ERROR = "error"
    RECOVERING = "recovering"


class MockAgent:
    """Mock agent class for testing."""
    
    def __init__(self, agent_id: str = "test_agent", user_id: str = None):
        self.agent_id = agent_id
        self.user_id = user_id
        self.state = AgentState.IDLE
        self.error_count = 0
        self.last_error = None
        self.should_fail = False
        self.failure_message = "Test failure"
        self.execution_time = 0.1
        
    async def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Mock process request method."""
        if self.should_fail:
            from netra_backend.app.core.exceptions_base import NetraException
            raise NetraException(self.failure_message)
        
        # Simulate execution time
        await asyncio.sleep(self.execution_time)
        return {"status": "success", "result": "processed"}
        
    async def recover(self) -> bool:
        """Mock recovery method."""
        self.state = AgentState.ACTIVE
        return True
    
    async def run(self, request: str, run_id: str, user_id: str, task_id: str):
        """Mock run method for state transitions."""
        self.state = AgentState.RUNNING
        result = await self.process_request({"request": request, "run_id": run_id})
        self.state = AgentState.IDLE
        return result


class MockOrchestrator:
    """Mock orchestrator for testing."""
    
    def __init__(self):
        self.agents: Dict[str, MockAgent] = {}
        self.agent_pool = []
        self.error_threshold = 3
        self.recovery_timeout = 5.0
        self.retry_delay = 0.1
        self.execution_timeout = 0.5
        self.max_concurrent_agents = 10
        self.metrics = {
            "agents_created": 0,
            "tasks_executed": 0, 
            "errors_handled": 0,
            "total_executions": 0,
            "failed_executions": 0,
            "total_execution_time": 0.0,
            "concurrent_peak": 0,
        }
        self._active_agents_override = None
    
    @property
    def active_agents(self) -> int:
        """Return count of active agents."""
        if self._active_agents_override is not None:
            return self._active_agents_override
        return len([agent for agent in self.agents.values() 
                   if agent.state in [AgentState.ACTIVE, AgentState.IDLE, AgentState.RUNNING]])
    
    @active_agents.setter
    def active_agents(self, value: int):
        """Set active agents count override for testing."""
        self._active_agents_override = value
    
    @property
    def orchestration_metrics(self) -> Dict[str, Any]:
        """Return orchestration metrics (alias for metrics)."""
        return getattr(self, 'metrics', {})
        
        
    async def handle_agent_error(self, agent: MockAgent, error: Exception) -> bool:
        """Handle agent error."""
        agent.error_count += 1
        agent.last_error = error
        agent.state = AgentState.ERROR
        return agent.error_count < self.error_threshold
    
    async def release_agent(self, user_id: str):
        """Release agent to the pool."""
        if user_id in self.agents:
            agent = self.agents[user_id]
            agent.state = AgentState.IDLE
            self.agent_pool.append(agent)
            del self.agents[user_id]
    
    async def get_or_create_agent(self, user_id: str) -> MockAgent:
        """Get or create a mock agent."""
        if self.active_agents >= self.max_concurrent_agents:
            from netra_backend.app.core.exceptions_base import NetraException
            raise NetraException("Maximum concurrent agents reached")
            
        if user_id not in self.agents:
            # Try to reuse from pool first
            if self.agent_pool:
                agent = self.agent_pool.pop(0)
                agent.user_id = user_id
                agent.agent_id = f"agent_{user_id}"
                agent.state = AgentState.ACTIVE
                self.agents[user_id] = agent
            else:
                agent = MockAgent(f"agent_{user_id}", user_id=user_id)
                agent.state = AgentState.IDLE  # Keep initial state as IDLE
                self.agents[user_id] = agent
                self.metrics["agents_created"] += 1
        
        # Track concurrent peak
        current_active = len(self.agents)
        if current_active > self.metrics.get("concurrent_peak", 0):
            self.metrics["concurrent_peak"] = current_active
            
        return self.agents[user_id]
    
    async def execute_agent_task(self, user_id: str, task: str, run_id: str, with_streaming: bool = False) -> Dict[str, Any]:
        """Execute a task with an agent."""
        import time
        start_time = time.time()
        
        agent = await self.get_or_create_agent(user_id)
        
        try:
            result = await asyncio.wait_for(
                agent.process_request({"task": task, "run_id": run_id}),
                timeout=self.execution_timeout
            )
            
            execution_time = time.time() - start_time
            self.metrics["tasks_executed"] += 1
            self.metrics["total_executions"] += 1
            self.metrics["total_execution_time"] += execution_time
            
            return {"status": "completed", "result": result, "run_id": run_id}
        except asyncio.TimeoutError:
            self.metrics["failed_executions"] += 1
            return {"status": "timeout", "error": "Task execution timed out"}
        except Exception as e:
            self.metrics["errors_handled"] += 1
            self.metrics["failed_executions"] += 1
            await self.handle_agent_error(agent, e)
            raise
    
    def get_orchestration_metrics(self) -> Dict[str, Any]:
        """Get orchestration metrics."""
        total_executions = self.metrics["total_executions"]
        failed_executions = self.metrics["failed_executions"]
        
        if total_executions > 0:
            success_rate = ((total_executions - failed_executions) / total_executions) * 100
            avg_execution_time = self.metrics["total_execution_time"] / total_executions
        else:
            success_rate = 0.0
            avg_execution_time = 0.0
            
        return {
            "total_executions": total_executions,
            "failed_executions": failed_executions,
            "success_rate": success_rate,
            "average_execution_time": avg_execution_time,
            "agents_created": self.metrics["agents_created"],
            "tasks_executed": self.metrics["tasks_executed"],
            "errors_handled": self.metrics["errors_handled"],
            "concurrent_peak": self.metrics["concurrent_peak"],
            "active_agents": self.active_agents,
            "pooled_agents": len(self.agent_pool)
        }