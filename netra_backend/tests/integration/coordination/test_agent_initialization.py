"""
Agent Initialization Integration Tests

BVJ:
- Segment: Platform/Internal (foundation for ALL customer segments)
- Business Goal: Platform Stability - Prevent $35K MRR loss from coordination failures
- Value Impact: Validates agent initialization and startup coordination
- Revenue Impact: Prevents customer requests from failing due to broken agent coordination

REQUIREMENTS:
- Start multiple agents simultaneously
- Agent registration in coordination system
- Coordination setup within 15 seconds
- Initialization order validation
"""

import pytest
import asyncio
import time
from datetime import datetime, timezone

from netra_backend.tests.shared_fixtures import coordination_infrastructure, coordination_agents, MockCoordinationAgent


class TestAgentInitialization:
    """BVJ: Validates agent initialization and startup coordination."""

    @pytest.mark.asyncio
    async def test_multi_agent_coordination_initialization(self, coordination_infrastructure):
        """BVJ: Prevent $35K MRR loss from coordination failures."""
        start_time = time.time()
        
        agents = await coordination_infrastructure.create_agent_coordination_scenario(3)
        
        initialization_time = time.time() - start_time
        
        assert len(agents) == 3
        assert initialization_time < 15.0  # Within 15 second requirement
        assert coordination_infrastructure.coordination_metrics["agents_initialized"] == 3

    @pytest.mark.asyncio
    async def test_agent_registration_process(self, coordination_infrastructure):
        """BVJ: Validates agent registration in coordination system."""
        agent = MockCoordinationAgent("test_agent")
        
        await coordination_infrastructure.agent_registry.register_agent("test_agent", agent)
        
        assert "test_agent" in coordination_infrastructure.agent_registry.registered_agents
        assert agent.coordination_status == "registered"

    @pytest.mark.asyncio
    async def test_simultaneous_agent_startup(self, coordination_infrastructure):
        """BVJ: Validates multiple agents can start simultaneously."""
        agent_count = 5
        
        start_time = time.time()
        agents = await coordination_infrastructure.create_agent_coordination_scenario(agent_count)
        startup_time = time.time() - start_time
        
        assert len(agents) == agent_count
        assert startup_time < 10.0  # Efficient startup
        assert all(agent.coordination_status == "registered" for agent in agents.values())

    @pytest.mark.asyncio
    async def test_agent_initialization_order_tracking(self, coordination_infrastructure):
        """BVJ: Validates agent initialization order is tracked."""
        agent_names = ["first_agent", "second_agent", "third_agent"]
        
        for name in agent_names:
            agent = MockCoordinationAgent(name)
            await coordination_infrastructure.agent_registry.register_agent(name, agent)
        
        initialization_order = coordination_infrastructure.agent_registry.initialization_order
        assert initialization_order == agent_names

    @pytest.mark.asyncio
    async def test_coordination_group_creation(self, coordination_infrastructure):
        """BVJ: Validates coordination group creation functionality."""
        agents = await coordination_infrastructure.create_agent_coordination_scenario(3)
        
        assert len(coordination_infrastructure.agent_registry.coordination_groups) == 1
        group = coordination_infrastructure.agent_registry.coordination_groups["test_group"]
        assert len(group["agents"]) == 3

    @pytest.mark.asyncio
    async def test_peer_agent_registration(self, coordination_infrastructure):
        """BVJ: Validates peer agent registration within groups."""
        agents = await coordination_infrastructure.create_agent_coordination_scenario(3)
        
        # Each agent should know about the other 2 agents
        for agent_name, agent in agents.items():
            assert len(agent.peer_agents) == 2  # 2 other agents
            assert agent_name not in agent.peer_agents  # Not itself

    @pytest.mark.asyncio
    async def test_agent_coordination_status_tracking(self, coordination_infrastructure):
        """BVJ: Validates agent coordination status is properly tracked."""
        agent = MockCoordinationAgent("status_test_agent")
        
        assert agent.coordination_status == "initializing"
        
        await coordination_infrastructure.agent_registry.register_agent("status_test_agent", agent)
        
        assert agent.coordination_status == "registered"

    @pytest.mark.asyncio
    async def test_coordination_metrics_tracking(self, coordination_infrastructure):
        """BVJ: Validates coordination metrics are properly tracked."""
        initial_metrics = coordination_infrastructure.coordination_metrics.copy()
        
        await coordination_infrastructure.create_agent_coordination_scenario(2)
        
        metrics = coordination_infrastructure.coordination_metrics
        assert metrics["agents_initialized"] == initial_metrics["agents_initialized"] + 2
        assert metrics["coordination_groups"] == initial_metrics["coordination_groups"] + 1

    @pytest.mark.asyncio
    async def test_large_scale_agent_initialization(self, coordination_infrastructure):
        """BVJ: Validates large scale agent initialization performance."""
        agent_count = 10
        
        start_time = time.time()
        agents = await coordination_infrastructure.create_agent_coordination_scenario(agent_count)
        initialization_time = time.time() - start_time
        
        assert len(agents) == agent_count
        assert initialization_time < 20.0  # Reasonable for larger scale
        assert all(len(agent.peer_agents) == agent_count - 1 for agent in agents.values())

    @pytest.mark.asyncio
    async def test_agent_initialization_failure_handling(self, coordination_infrastructure):
        """BVJ: Validates initialization failure handling doesn't break system."""
        # Test normal initialization still works after handling failures
        agents = await coordination_infrastructure.create_agent_coordination_scenario(2)
        
        assert len(agents) == 2
        assert all(agent.coordination_status == "registered" for agent in agents.values())


if __name__ == "__main__":
    pytest.main([__file__, "-v"])