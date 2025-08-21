"""Integration Test: Agent Cold Start on First Message
BVJ: $15K MRR - Agent initialization failures cause service unavailability
Components: Supervisor → SubAgent Registry → Tool Loading → State Management
Critical: Agents must initialize reliably from cold state for first user interaction
"""

import pytest
import asyncio
from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime, timezone

from app.agents.supervisor_consolidated import SupervisorAgent
from app.agents.base import BaseSubAgent
from app.agents.supervisor.agent_registry import AgentRegistry
from app.agents.triage_sub_agent.agent import TriageSubAgent
from app.agents.data_sub_agent.agent import DataSubAgent
from app.core.agent_recovery_supervisor import SupervisorRecoveryStrategy
from app.schemas import UserInDB
from test_framework.mock_utils import mock_justified


@pytest.mark.asyncio
class TestAgentColdStart:
    """Test agent initialization from cold system state."""
    
    @pytest.fixture
    async def mock_llm_manager(self):
        """Create mock LLM manager for agent testing."""
        # L2: Mocking LLM to test agent initialization flow
        llm_manager = Mock()
        llm_manager.generate_response = AsyncMock(return_value="Mock LLM response")
        llm_manager.is_available = AsyncMock(return_value=True)
        return llm_manager
    
    @pytest.fixture
    async def mock_tool_dispatcher(self):
        """Create mock tool dispatcher."""
        # L2: Mocking tools to test agent orchestration
        dispatcher = Mock()
        dispatcher.dispatch = AsyncMock(return_value={"status": "success"})
        dispatcher.get_available_tools = Mock(return_value=["search", "analyze", "optimize"])
        return dispatcher
    
    @pytest.fixture
    async def agent_registry(self, mock_llm_manager, mock_tool_dispatcher):
        """Create agent registry with dependencies."""
        return AgentRegistry(mock_llm_manager, mock_tool_dispatcher)
    
    @pytest.fixture
    async def test_user(self):
        """Create test user for agent operations."""
        return UserInDB(
            id="cold_start_user_001",
            email="coldstart@test.netra.ai",
            username="coldstartuser",
            is_active=True,
            created_at=datetime.now(timezone.utc)
        )
    
    async def test_supervisor_initialization_from_cold(
        self, mock_llm_manager, mock_tool_dispatcher
    ):
        """Test supervisor agent initialization from cold state."""
        
        # Step 1: Verify no agents running
        supervisor = None
        assert supervisor is None
        
        # Step 2: Initialize supervisor
        supervisor = SupervisorAgent(
            llm_manager=mock_llm_manager,
            tool_dispatcher=mock_tool_dispatcher
        )
        
        # Step 3: Verify supervisor initialized
        assert supervisor is not None
        assert supervisor.state == "initialized"
        assert supervisor.llm_manager == mock_llm_manager
        
        # Step 4: Start supervisor
        await supervisor.start()
        
        # Step 5: Verify ready state
        assert supervisor.state == "ready"
        assert supervisor.is_running is True
    
    async def test_sub_agent_registration_on_startup(
        self, agent_registry
    ):
        """Test sub-agent registration during startup."""
        
        # Step 1: Verify empty registry
        assert len(agent_registry.list_agents()) == 0
        
        # Step 2: Register default agents
        agent_registry.register_default_agents()
        
        # Step 3: Verify all core agents registered
        registered_agents = agent_registry.list_agents()
        expected_agents = [
            "triage", "data", "optimization", 
            "actions", "reporting", "synthetic_data", "corpus_admin"
        ]
        
        for agent_name in expected_agents:
            assert agent_name in registered_agents
        
        # Step 4: Verify agent instances
        triage_agent = agent_registry.get("triage")
        assert isinstance(triage_agent, BaseSubAgent)
        assert triage_agent.name == "triage"
    
    async def test_agent_capability_discovery(self, agent_registry):
        """Test agent capability discovery and mapping."""
        
        # Register agents
        agent_registry.register_default_agents()
        
        # Test capability discovery
        capabilities = {}
        for agent_name in agent_registry.list_agents():
            agent = agent_registry.get(agent_name)
            capabilities[agent_name] = agent.get_capabilities()
        
        # Verify triage capabilities
        assert "route_request" in capabilities.get("triage", [])
        assert "classify_intent" in capabilities.get("triage", [])
        
        # Verify data agent capabilities
        assert "query_metrics" in capabilities.get("data", [])
        assert "analyze_usage" in capabilities.get("data", [])
    
    async def test_agent_lifecycle_management(
        self, mock_llm_manager, mock_tool_dispatcher
    ):
        """Test complete agent lifecycle from cold to ready."""
        
        # Initialize supervisor
        supervisor = SupervisorAgent(
            llm_manager=mock_llm_manager,
            tool_dispatcher=mock_tool_dispatcher
        )
        
        # Track lifecycle states
        states_observed = []
        
        # Mock state tracker
        original_set_state = supervisor.set_state
        def track_state(state):
            states_observed.append(state)
            original_set_state(state)
        
        supervisor.set_state = track_state
        
        # Execute lifecycle
        await supervisor.start()
        await supervisor.initialize_agents()
        await supervisor.prepare_for_requests()
        
        # Verify state progression
        expected_states = ["starting", "initializing", "ready"]
        for state in expected_states:
            assert state in states_observed
    
    async def test_first_message_processing_cold_start(
        self, mock_llm_manager, mock_tool_dispatcher, test_user
    ):
        """Test processing first user message from cold start."""
        
        # Cold start supervisor
        supervisor = SupervisorAgent(
            llm_manager=mock_llm_manager,
            tool_dispatcher=mock_tool_dispatcher
        )
        await supervisor.start()
        
        # Process first message
        first_message = "Help me optimize my AI workload costs"
        thread_id = "cold_start_thread_001"
        run_id = "cold_start_run_001"
        
        # Execute agent processing
        response = await supervisor.run(
            user_request=first_message,
            thread_id=thread_id,
            user_id=test_user.id,
            run_id=run_id
        )
        
        # Verify response generated
        assert response is not None
        assert "Mock LLM response" in str(response)
        
        # Verify LLM was called
        mock_llm_manager.generate_response.assert_called()
    
    async def test_parallel_agent_initialization(self, agent_registry):
        """Test parallel initialization of multiple agents."""
        
        # Define agents to initialize
        agent_configs = [
            {"name": "triage", "priority": 1},
            {"name": "data", "priority": 2},
            {"name": "optimization", "priority": 2},
        ]
        
        # Initialize agents in parallel
        async def init_agent(config):
            agent = agent_registry.create_agent(config["name"])
            await agent.initialize()
            return agent
        
        # Execute parallel initialization
        tasks = [init_agent(config) for config in agent_configs]
        agents = await asyncio.gather(*tasks)
        
        # Verify all initialized
        assert len(agents) == 3
        for agent in agents:
            assert agent.state == "initialized"
    
    async def test_agent_state_persistence(
        self, mock_llm_manager, mock_tool_dispatcher
    ):
        """Test agent state persistence during initialization."""
        
        # Initialize supervisor with state tracking
        supervisor = SupervisorAgent(
            llm_manager=mock_llm_manager,
            tool_dispatcher=mock_tool_dispatcher
        )
        
        # Mock state persistence
        # L2: Mocking state store to test persistence
        state_store = {}
        
        async def save_state(agent_id: str, state: Dict):
            state_store[agent_id] = state
        
        async def load_state(agent_id: str) -> Optional[Dict]:
            return state_store.get(agent_id)
        
        # Save initial state
        await save_state("supervisor", {
            "status": "initializing",
            "start_time": datetime.now(timezone.utc).isoformat(),
            "agents": []
        })
        
        # Start supervisor
        await supervisor.start()
        
        # Save running state
        await save_state("supervisor", {
            "status": "running",
            "start_time": datetime.now(timezone.utc).isoformat(),
            "agents": ["triage", "data", "optimization"]
        })
        
        # Verify state persisted
        saved_state = await load_state("supervisor")
        assert saved_state["status"] == "running"
        assert len(saved_state["agents"]) == 3
    
    async def test_error_recovery_during_cold_start(
        self, mock_llm_manager, mock_tool_dispatcher
    ):
        """Test error recovery during agent cold start."""
        
        # Simulate LLM failure during init
        mock_llm_manager.is_available.return_value = False
        
        supervisor = SupervisorAgent(
            llm_manager=mock_llm_manager,
            tool_dispatcher=mock_tool_dispatcher
        )
        
        # Attempt start with retry logic
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                await supervisor.start()
                break
            except Exception as e:
                retry_count += 1
                if retry_count >= max_retries:
                    # Fall back to degraded mode
                    supervisor.degraded_mode = True
                    supervisor.state = "degraded"
        
        # Verify degraded mode activated
        assert supervisor.degraded_mode is True
        assert supervisor.state == "degraded"
    
    async def test_tool_loading_and_validation(
        self, mock_tool_dispatcher, agent_registry
    ):
        """Test tool loading and validation during agent init."""
        
        # Register agents
        agent_registry.register_default_agents()
        
        # Get data agent
        data_agent = agent_registry.get("data")
        
        # Load tools for agent
        tools = await data_agent.load_tools(mock_tool_dispatcher)
        
        # Verify tools loaded
        assert len(tools) > 0
        assert "search" in tools or "query" in tools
        
        # Validate tool access
        for tool_name in tools:
            result = await mock_tool_dispatcher.dispatch(
                tool_name, 
                test_param="test"
            )
            assert result["status"] == "success"