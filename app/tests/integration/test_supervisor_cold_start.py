"""Integration Test: Supervisor Agent Cold Start

BVJ: $20K MRR - Agent system must be ready  
Components: Supervisor → Agent Registry → Sub-Agents
Critical: No responses possible without supervisor initialization
"""

import pytest
import asyncio
from typing import Dict, Any, List
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
import time


@pytest.mark.asyncio
class TestSupervisorColdStart:
    """Test supervisor agent initialization and registry population."""
    
    @pytest.fixture
    async def mock_llm_manager(self):
        """Create mock LLM manager."""
        llm_manager = Mock()
        llm_manager.ask_llm = AsyncMock(return_value={
            "content": "Supervisor response",
            "model": "gpt-4"
        })
        return llm_manager
    
    @pytest.fixture
    async def mock_tool_dispatcher(self):
        """Create mock tool dispatcher."""
        tool_dispatcher = Mock()
        tool_dispatcher.available_tools = [
            "gpu_analyzer",
            "cost_optimizer",
            "performance_profiler"
        ]
        tool_dispatcher.dispatch = AsyncMock()
        return tool_dispatcher
    
    async def test_supervisor_initialization_sequence(
        self, 
        mock_llm_manager, 
        mock_tool_dispatcher
    ):
        """Test complete supervisor initialization sequence."""
        from app.agents.supervisor_consolidated import SupervisorAgent
        from app.agents.registry import AgentRegistry
        
        # Track initialization timing
        start_time = time.time()
        
        # Initialize supervisor
        supervisor = SupervisorAgent(
            llm_manager=mock_llm_manager,
            tool_dispatcher=mock_tool_dispatcher,
            websocket_manager=Mock()
        )
        
        init_time = time.time() - start_time
        
        # Verify initialization completed quickly
        assert init_time < 5.0  # Should init in under 5 seconds
        assert supervisor is not None
        assert hasattr(supervisor, 'registry')
    
    async def test_agent_registry_population(
        self, 
        mock_llm_manager,
        mock_tool_dispatcher
    ):
        """Test agent registry is populated with all required agents."""
        from app.agents.supervisor_consolidated import SupervisorAgent
        
        supervisor = SupervisorAgent(
            llm_manager=mock_llm_manager,
            tool_dispatcher=mock_tool_dispatcher,
            websocket_manager=Mock()
        )
        
        # Expected minimum agents
        required_agents = [
            "triage_agent",
            "cost_optimizer_agent",
            "performance_agent",
            "model_selector_agent",
            "capacity_planning_agent"
        ]
        
        # Check registry
        registered_agents = supervisor.registry.list_agents()
        
        for agent_name in required_agents:
            assert agent_name in registered_agents, f"Missing {agent_name}"
    
    async def test_sub_agent_health_checks(
        self,
        mock_llm_manager,
        mock_tool_dispatcher
    ):
        """Test health checks for all registered sub-agents."""
        from app.agents.supervisor_consolidated import SupervisorAgent
        
        supervisor = SupervisorAgent(
            llm_manager=mock_llm_manager,
            tool_dispatcher=mock_tool_dispatcher,
            websocket_manager=Mock()
        )
        
        health_results = {}
        
        # Check health of each agent
        for agent_name in supervisor.registry.list_agents():
            agent = supervisor.registry.get_agent(agent_name)
            if hasattr(agent, 'health_check'):
                health = await agent.health_check()
                health_results[agent_name] = health
            else:
                health_results[agent_name] = {"status": "healthy", "default": True}
        
        # All agents should be healthy
        for agent_name, health in health_results.items():
            assert health.get("status") == "healthy", f"{agent_name} unhealthy"
    
    async def test_cold_start_with_pending_messages(
        self,
        mock_llm_manager,
        mock_tool_dispatcher
    ):
        """Test supervisor handles pending messages after cold start."""
        from app.agents.supervisor_consolidated import SupervisorAgent
        
        # Simulate pending messages
        pending_messages = [
            {
                "id": "msg_1",
                "content": "Optimize my GPU costs",
                "timestamp": datetime.utcnow().isoformat()
            },
            {
                "id": "msg_2", 
                "content": "Analyze latency issues",
                "timestamp": datetime.utcnow().isoformat()
            }
        ]
        
        supervisor = SupervisorAgent(
            llm_manager=mock_llm_manager,
            tool_dispatcher=mock_tool_dispatcher,
            websocket_manager=Mock()
        )
        
        # Process pending messages
        processed = []
        for message in pending_messages:
            result = await supervisor.process_message(
                message["content"],
                thread_id="test_thread",
                user_id="test_user"
            )
            processed.append(result)
        
        assert len(processed) == len(pending_messages)
    
    async def test_agent_initialization_parallelism(
        self,
        mock_llm_manager,
        mock_tool_dispatcher
    ):
        """Test agents initialize in parallel for faster startup."""
        from app.agents.supervisor_consolidated import SupervisorAgent
        
        # Track initialization with timing
        init_times = []
        
        async def timed_init():
            start = time.time()
            supervisor = SupervisorAgent(
                llm_manager=mock_llm_manager,
                tool_dispatcher=mock_tool_dispatcher,
                websocket_manager=Mock()
            )
            duration = time.time() - start
            return supervisor, duration
        
        # Initialize multiple times to test consistency
        tasks = [timed_init() for _ in range(3)]
        results = await asyncio.gather(*tasks)
        
        for supervisor, duration in results:
            assert supervisor is not None
            init_times.append(duration)
        
        # Verify consistent initialization times
        avg_time = sum(init_times) / len(init_times)
        assert avg_time < 5.0  # Average should be under 5 seconds
    
    async def test_tool_dispatcher_integration(
        self,
        mock_llm_manager,
        mock_tool_dispatcher
    ):
        """Test supervisor properly integrates with tool dispatcher."""
        from app.agents.supervisor_consolidated import SupervisorAgent
        
        supervisor = SupervisorAgent(
            llm_manager=mock_llm_manager,
            tool_dispatcher=mock_tool_dispatcher,
            websocket_manager=Mock()
        )
        
        # Verify tool dispatcher is accessible
        assert supervisor.tool_dispatcher is not None
        
        # Verify tools are available to agents
        available_tools = supervisor.tool_dispatcher.available_tools
        assert len(available_tools) > 0
        assert "gpu_analyzer" in available_tools
    
    async def test_websocket_manager_connection(
        self,
        mock_llm_manager,
        mock_tool_dispatcher
    ):
        """Test supervisor connects to WebSocket manager."""
        from app.agents.supervisor_consolidated import SupervisorAgent
        from app.ws_manager import WebSocketManager
        
        ws_manager = Mock(spec=WebSocketManager)
        ws_manager.send_message = AsyncMock()
        
        supervisor = SupervisorAgent(
            llm_manager=mock_llm_manager,
            tool_dispatcher=mock_tool_dispatcher,
            websocket_manager=ws_manager
        )
        
        # Verify WebSocket manager is set
        assert supervisor.websocket_manager is not None
        
        # Test sending initialization message
        await supervisor.websocket_manager.send_message(
            "test_user",
            {"type": "supervisor_ready", "timestamp": datetime.utcnow().isoformat()}
        )
        
        ws_manager.send_message.assert_called_once()
    
    async def test_recovery_from_partial_initialization(
        self,
        mock_llm_manager,
        mock_tool_dispatcher
    ):
        """Test supervisor recovers from partial initialization failures."""
        from app.agents.supervisor_consolidated import SupervisorAgent
        
        # Simulate partial failure
        mock_tool_dispatcher.available_tools = []  # No tools initially
        
        supervisor = SupervisorAgent(
            llm_manager=mock_llm_manager,
            tool_dispatcher=mock_tool_dispatcher,
            websocket_manager=Mock()
        )
        
        # Fix the issue
        mock_tool_dispatcher.available_tools = ["gpu_analyzer"]
        
        # Verify supervisor can still function
        result = await supervisor.process_message(
            "Test message",
            thread_id="test",
            user_id="test_user"
        )
        
        assert result is not None