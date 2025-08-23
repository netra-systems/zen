"""Mock classes for agent service testing.

This module provides mock classes and enums for testing agent services.
"""

import asyncio
from enum import Enum
from unittest.mock import AsyncMock, MagicMock
from typing import Dict, Any, Optional


class AgentState(Enum):
    """Mock agent state enum."""
    IDLE = "idle"
    ACTIVE = "active"
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


class MockOrchestrator:
    """Mock orchestrator for testing."""
    
    def __init__(self):
        self.agents: Dict[str, MockAgent] = {}
        self.error_threshold = 3
        self.recovery_timeout = 5.0
        self.retry_delay = 0.1
        self.execution_timeout = 0.5
    
    @property
    def active_agents(self) -> int:
        """Return count of active agents."""
        return len([agent for agent in self.agents.values() 
                   if agent.state in [AgentState.ACTIVE, AgentState.IDLE]])
    
    @property
    def orchestration_metrics(self) -> Dict[str, Any]:
        """Return orchestration metrics (alias for metrics)."""
        return getattr(self, 'metrics', {})
        
    async def get_or_create_agent(self, user_id: str) -> MockAgent:
        """Get or create a mock agent."""
        if user_id not in self.agents:
            agent = MockAgent(f"agent_{user_id}", user_id=user_id)
            agent.state = AgentState.ACTIVE  # Set agent as active
            self.agents[user_id] = agent
            # Update metrics
            if hasattr(self, 'metrics'):
                self.metrics["agents_created"] += 1
        return self.agents[user_id]
        
    async def execute_agent_task(self, user_id: str, task: str, run_id: str) -> Dict[str, Any]:
        """Execute a task with an agent."""
        agent = await self.get_or_create_agent(user_id)
        
        try:
            # Add timeout handling
            result = await asyncio.wait_for(
                agent.process_request({"task": task, "run_id": run_id}),
                timeout=self.execution_timeout
            )
            # Update metrics
            if hasattr(self, 'metrics'):
                self.metrics["tasks_executed"] += 1
            return {"status": "completed", "result": result}
        except asyncio.TimeoutError:
            return {"status": "timeout", "error": "Task execution timed out"}
        except Exception as e:
            # Update error metrics
            if hasattr(self, 'metrics'):
                self.metrics["errors_handled"] += 1
            await self.handle_agent_error(agent, e)
            raise
        
    async def handle_agent_error(self, agent: MockAgent, error: Exception) -> bool:
        """Handle agent error."""
        agent.error_count += 1
        agent.last_error = error
        agent.state = AgentState.ERROR
        return agent.error_count < self.error_threshold