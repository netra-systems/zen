"""
Shared fixtures and utilities for multi-agent coordination integration tests.

BVJ:
- Segment: Platform/Internal (foundation for ALL customer segments)
- Business Goal: Platform Stability - Prevent $35K MRR loss from coordination failures
- Value Impact: Ensures start multiple agents → establish communication → verify message passing
- Revenue Impact: Prevents customer requests from failing due to broken agent coordination
"""

# Set testing environment

from datetime import datetime, timezone
from netra_backend.app.websocket_core import WebSocketManager as WebSocketManager
from typing import Any, Callable, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch
import asyncio
import os
import pytest
import time
import uuid

os.environ["TESTING"] = "1"

os.environ["ENVIRONMENT"] = "testing"

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

from netra_backend.app.agents.base_agent import BaseSubAgent
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.logging_config import central_logger
from netra_backend.app.websocket_core import UnifiedWebSocketManager as WebSocketManager

logger = central_logger.get_logger(__name__)

class MockCoordinationAgent(BaseSubAgent):

    """Mock agent with coordination capabilities."""
    
    def __init__(self, name: str, llm_manager=None):

        super().__init__(llm_manager, name=name)

        self.peer_agents = {}

        self.message_inbox = []

        self.message_outbox = []

        self.coordination_status = "initializing"

        self.coordination_channels = {}

        self.heartbeat_interval = 1.0

        self.last_heartbeat = None
    
    async def execute(self, request: Dict[str, Any], state: DeepAgentState) -> Dict[str, Any]:

        """Execute with coordination tracking."""

        execution_id = str(uuid.uuid4())
        
        if "coordination_action" in request:

            return await self._handle_coordination_action(request, execution_id)
        
        return {

            "status": "success",

            "execution_id": execution_id,

            "agent": self.name,

            "coordination_status": self.coordination_status,

            "peer_count": len(self.peer_agents)

        }
    
    async def _handle_coordination_action(self, request: Dict[str, Any], execution_id: str) -> Dict[str, Any]:

        """Handle coordination-specific actions."""

        action = request["coordination_action"]
        
        if action == "register_peer":

            peer_name = request["peer_name"]

            peer_agent = request["peer_agent"]

            await self.register_peer(peer_name, peer_agent)
            
        elif action == "send_message":

            target = request["target"]

            message = request["message"]

            await self.send_message(target, message)
            
        elif action == "broadcast":

            message = request["message"]

            await self.broadcast_message(message)
            
        elif action == "heartbeat":

            await self.send_heartbeat()
        
        return {

            "status": "success",

            "execution_id": execution_id,

            "action": action,

            "coordination_status": self.coordination_status

        }
    
    async def register_peer(self, peer_name: str, peer_agent: 'MockCoordinationAgent'):

        """Register a peer agent for coordination."""

        self.peer_agents[peer_name] = peer_agent

        self.coordination_channels[peer_name] = {"status": "active", "last_contact": datetime.now(timezone.utc)}
    
    async def send_message(self, target: str, message: Dict[str, Any]):

        """Send message to specific peer agent."""

        if target in self.peer_agents:

            message_envelope = {

                "from": self.name,

                "to": target,

                "message": message,

                "timestamp": datetime.now(timezone.utc),

                "message_id": str(uuid.uuid4())

            }
            
            self.message_outbox.append(message_envelope)

            await self.peer_agents[target].receive_message(message_envelope)
    
    async def receive_message(self, message_envelope: Dict[str, Any]):

        """Receive message from peer agent."""

        self.message_inbox.append(message_envelope)
    
    async def broadcast_message(self, message: Dict[str, Any]):

        """Broadcast message to all peer agents."""

        for peer_name in self.peer_agents:

            await self.send_message(peer_name, message)
    
    async def send_heartbeat(self):

        """Send heartbeat to all peers."""

        heartbeat = {"type": "heartbeat", "agent": self.name, "timestamp": datetime.now(timezone.utc)}

        await self.broadcast_message(heartbeat)

        self.last_heartbeat = datetime.now(timezone.utc)

class MockAgentRegistry:

    """Mock agent registry for coordination testing."""
    
    def __init__(self):

        self.registered_agents = {}

        self.coordination_groups = {}

        self.initialization_order = []
        
    async def register_agent(self, agent_name: str, agent: MockCoordinationAgent):

        """Register agent in the coordination system."""

        self.registered_agents[agent_name] = agent

        self.initialization_order.append(agent_name)

        agent.coordination_status = "registered"
    
    async def create_coordination_group(self, group_name: str, agent_names: List[str]):

        """Create coordination group with specified agents."""

        self.coordination_groups[group_name] = {"agents": agent_names, "created_at": datetime.now(timezone.utc)}
        
        # Establish peer connections within the group

        for i, agent_name in enumerate(agent_names):

            if agent_name in self.registered_agents:

                agent = self.registered_agents[agent_name]

                for other_agent_name in agent_names:

                    if other_agent_name != agent_name and other_agent_name in self.registered_agents:

                        other_agent = self.registered_agents[other_agent_name]

                        await agent.register_peer(other_agent_name, other_agent)

class MockCoordinationInfrastructure:

    """Mock coordination infrastructure for testing."""
    
    def __init__(self):

        self.agent_registry = MockAgentRegistry()

        self.llm_manager = Mock(spec=LLMManager)

        self.websocket_manager = Mock(spec=WebSocketManager)

        self.tool_dispatcher = Mock(spec=ToolDispatcher)

        self.coordination_metrics = {

            "agents_initialized": 0,

            "messages_sent": 0,

            "coordination_groups": 0,

            "heartbeats_sent": 0

        }
    
    async def create_agent_coordination_scenario(self, agent_count: int = 3):

        """Create multi-agent coordination scenario."""

        agents = {}
        
        # Create agents

        for i in range(agent_count):

            agent_name = f"coord_agent_{i}"

            agent = MockCoordinationAgent(agent_name, self.llm_manager)

            agents[agent_name] = agent

            await self.agent_registry.register_agent(agent_name, agent)

            self.coordination_metrics["agents_initialized"] += 1
        
        # Create coordination group

        agent_names = list(agents.keys())

        await self.agent_registry.create_coordination_group("test_group", agent_names)

        self.coordination_metrics["coordination_groups"] += 1
        
        return agents

@pytest.fixture

async def coordination_infrastructure():

    """Setup coordination infrastructure."""

    return MockCoordinationInfrastructure()

@pytest.fixture

async def coordination_agents(coordination_infrastructure):

    """Create coordination agents for testing."""

    return await coordination_infrastructure.create_agent_coordination_scenario()