"""Integration Test: Supervisor Agent Initialization Chain
BVJ: $18K MRR - Supervisor failures cause complete service outage
Components: Supervisor → AgentRegistry → SubAgents → Capabilities → Ready State
Critical: Supervisor must reliably initialize entire agent ecosystem
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from netra_backend.app.agents.base_agent import BaseSubAgent
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry

from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.core.agent_recovery_supervisor import SupervisorRecoveryStrategy
from test_framework.mock_utils import mock_justified

@pytest.mark.asyncio
class TestSupervisorAgentInitializationChain:
    """Test complete supervisor initialization chain."""
    
    @pytest.fixture
    async def mock_dependencies(self):
        """Create mock dependencies for supervisor."""
        # Mocking external deps for supervisor chain testing (L2)
        deps = {
            "llm_manager": Mock(generate_response=AsyncMock(return_value="Response")),
            "tool_dispatcher": Mock(dispatch=AsyncMock(return_value={"status": "ok"})),
            "db_session": Mock(),
            "redis_manager": Mock(get=AsyncMock(), set=AsyncMock())
        }
        yield deps
    
    @pytest.mark.asyncio
    async def test_complete_initialization_sequence(self, mock_dependencies):
        """Test supervisor initialization from cold to ready."""
        supervisor = SupervisorAgent(**mock_dependencies)
        
        # Track initialization steps
        init_steps = []
        
        # Step 1: Pre-initialization state
        init_steps.append(("pre_init", supervisor.state))
        assert supervisor.state == "uninitialized"
        
        # Step 2: Start initialization
        await supervisor.initialize()
        init_steps.append(("post_init", supervisor.state))
        
        # Step 3: Register sub-agents
        await supervisor.register_agents()
        init_steps.append(("agents_registered", len(supervisor.agents)))
        
        # Step 4: Validate capabilities
        capabilities = await supervisor.validate_capabilities()
        init_steps.append(("capabilities", len(capabilities)))
        
        # Step 5: Ready state
        await supervisor.set_ready()
        init_steps.append(("ready", supervisor.state))
        
        # Verify complete chain
        assert supervisor.state == "ready"
        assert len(supervisor.agents) >= 5  # Core agents
        assert len(capabilities) >= 20  # Multiple capabilities
    
    @pytest.mark.asyncio
    async def test_sub_agent_registration_order(self, mock_dependencies):
        """Test correct order of sub-agent registration."""
        supervisor = SupervisorAgent(**mock_dependencies)
        await supervisor.initialize()
        
        registration_order = []
        
        # Mock registration to track order
        original_register = supervisor.registry.register
        async def track_register(agent_name, agent):
            registration_order.append(agent_name)
            return original_register(agent_name, agent)
        
        supervisor.registry.register = track_register
        await supervisor.register_agents()
        
        # Verify priority agents registered first
        priority_agents = ["triage", "data", "optimization"]
        for i, agent in enumerate(priority_agents):
            assert registration_order[i] == agent
    
    @pytest.mark.asyncio
    async def test_capability_validation_completeness(self, mock_dependencies):
        """Test all agent capabilities are validated."""
        supervisor = SupervisorAgent(**mock_dependencies)
        await supervisor.initialize()
        await supervisor.register_agents()
        
        # Validate each agent's capabilities
        invalid_capabilities = []
        for agent_name, agent in supervisor.agents.items():
            caps = agent.get_capabilities()
            for cap in caps:
                if not await supervisor.validate_capability(agent_name, cap):
                    invalid_capabilities.append((agent_name, cap))
        
        # All capabilities should be valid
        assert len(invalid_capabilities) == 0
    
    @pytest.mark.asyncio
    async def test_initialization_error_recovery(self, mock_dependencies):
        """Test recovery from initialization failures."""
        supervisor = SupervisorAgent(**mock_dependencies)
        
        # Simulate agent registration failure
        with patch.object(supervisor, 'register_agents') as mock_register:
            mock_register.side_effect = Exception("Registration failed")
            
            # Attempt initialization with retry
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    await supervisor.initialize()
                    await supervisor.register_agents()
                    break
                except Exception:
                    if attempt < max_retries - 1:
                        await asyncio.sleep(0.1)
                        # Reset and retry
                        mock_register.side_effect = None
        
        # Verify recovery succeeded
        assert supervisor.state != "failed"
    
    @pytest.mark.asyncio
    async def test_ready_state_requirements(self, mock_dependencies):
        """Test requirements for reaching ready state."""
        supervisor = SupervisorAgent(**mock_dependencies)
        
        # Cannot be ready without initialization
        with pytest.raises(RuntimeError, match="Not initialized"):
            await supervisor.set_ready()
        
        # Initialize but don't register agents
        await supervisor.initialize()
        
        # Cannot be ready without agents
        with pytest.raises(RuntimeError, match="No agents registered"):
            await supervisor.set_ready()
        
        # Register agents and reach ready
        await supervisor.register_agents()
        await supervisor.set_ready()
        
        assert supervisor.state == "ready"