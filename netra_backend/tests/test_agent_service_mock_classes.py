"""Mock classes for agent service testing.

This module provides mock classes and enums for testing agent services.
"""

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
    
    def __init__(self, agent_id: str = "test_agent"):
        self.agent_id = agent_id
        self.state = AgentState.IDLE
        self.error_count = 0
        self.last_error = None
        
    async def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Mock process request method."""
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
        
    async def get_or_create_agent(self, user_id: str) -> MockAgent:
        """Get or create a mock agent."""
        if user_id not in self.agents:
            self.agents[user_id] = MockAgent(f"agent_{user_id}")
        return self.agents[user_id]
        
    async def handle_agent_error(self, agent: MockAgent, error: Exception) -> bool:
        """Handle agent error."""
        agent.error_count += 1
        agent.last_error = error
        agent.state = AgentState.ERROR
        return agent.error_count < self.error_threshold