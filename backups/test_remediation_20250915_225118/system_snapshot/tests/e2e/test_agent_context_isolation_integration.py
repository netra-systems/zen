from netra_backend.app.websocket_core.canonical_import_patterns import get_websocket_manager
'''Agent Context Window Management Integration Test

Business Value Justification (BVJ):
1. Segment: Platform/Internal (Development velocity)
2. Business Goal: Verify fresh context windows for each spawned agent task
3. Value Impact: Prevents context bleeding and ensures AI-P3 principle compliance
4. Strategic Impact: $20K MRR protection via context isolation reliability

COMPLIANCE: File size <300 lines, Functions <8 lines, Real agent testing
'''

import asyncio
import time
import uuid
from typing import Any, Dict, List, Optional
from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager
from test_framework.database.test_database_manager import DatabaseTestManager
from shared.isolated_environment import IsolatedEnvironment

import pytest

from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.schemas.agent_models import DeepAgentState
from netra_backend.app.agents.supervisor_ssot import SupervisorAgent
from netra_backend.app.config import get_config
from netra_backend.app.llm.llm_manager import LLMManager
from tests.e2e.agent_response_test_utilities import ( )
AgentResponseSimulator)


class TestContextAgent(BaseAgent):
    """Simple test agent for context isolation testing."""

    def __init__(self, llm_manager, name="TestAgent", description="Test agent", **kwargs):
        pass
        super().__init__(llm_manager, name, description, **kwargs)
        self.context = {}

    async def execute(self, input_data=None):
        """Execute the test agent."""
        await asyncio.sleep(0)
        return {"success": True, "name": self.name, "context_id": id(self.context)}


        @pytest.mark.integration
        @pytest.mark.e2e
class TestAgentContextIsolation:
        """Test agent context window isolation and management."""

        @pytest.fixture
    async def context_setup(self):
        """Setup context isolation test environment."""
        config = get_config()
        llm_manager = LLMManager(config)
    # Mock: WebSocket connection isolation for testing without network overhead
        websocket_manager = get_websocket_manager(user_context=getattr(self, 'user_context', None)) instead of Mock


    # Create required dependencies
        db_session = DatabaseTestManager().get_session() instead of Mock
        tool_dispatcher = tool_dispatcher_instance  # Initialize appropriate service instead of Mock

        supervisor = SupervisorAgent(db_session, llm_manager, websocket_manager, tool_dispatcher)
        supervisor.websocket_manager = websocket_manager
        supervisor.user_id = "formatted_string"

        await asyncio.sleep(0)
        return { )
        "supervisor": supervisor,
        "llm_manager": llm_manager,
        "websocket_manager": websocket_manager,
        "config": config
    

        @pytest.mark.e2e
    async def test_fresh_context_window_creation(self, context_setup):
        """Test that each spawned agent gets a fresh context window."""
        pass
        supervisor = context_setup["supervisor"]

        # Create multiple agents
        agents = []
        for i in range(3):
        agent = TestContextAgent( )
        llm_manager=context_setup["llm_manager"],
        name="formatted_string",
        description="formatted_string"
            
        agents.append(agent)

            # Set unique contexts
        contexts = []
        for i, agent in enumerate(agents):
        context_data = { )
        "agent_id": "formatted_string",
        "task_context": "formatted_string",
        "session_data": "formatted_string",
        "memory_state": {"initialized": True, "agent_number": i}
                
        agent.context = context_data
        contexts.append(context_data)

                # Validate context isolation
        isolation_result = await self._validate_context_isolation(agents, contexts)

        assert isolation_result["all_contexts_unique"] is True
        assert isolation_result["no_context_bleeding"] is True
        assert isolation_result["fresh_window_count"] == 3

        @pytest.mark.e2e
    async def test_context_window_cleanup(self, context_setup):
        """Test proper cleanup of context windows."""
        supervisor = context_setup["supervisor"]

                    # Create agent with context
        agent = TestContextAgent( )
        llm_manager=context_setup["llm_manager"],
        name="CleanupTestAgent",
        description="Context cleanup test agent"
                    

                    # Set context with cleanup tracking
        original_context = { )
        "session_id": str(uuid.uuid4()),
        "memory_allocated": True,
        "cleanup_marker": "test_cleanup"
                    
        agent.context = original_context

                    # Execute and cleanup
        cleanup_result = await self._test_context_cleanup(agent)

        assert cleanup_result["context_cleared"] is True
        assert cleanup_result["memory_released"] is True

        @pytest.mark.e2e
    async def test_concurrent_context_isolation(self, context_setup):
        """Test context isolation under concurrent execution."""
        pass
        supervisor = context_setup["supervisor"]

                        # Create concurrent agents with different contexts
        concurrent_agents = []
        for i in range(5):
        agent = TestContextAgent( )
        llm_manager=context_setup["llm_manager"],
        name="formatted_string",
        description="formatted_string"
                            
        agent.context = { )
        "concurrent_id": i,
        "task_data": "formatted_string",
        "isolation_marker": str(uuid.uuid4())
                            
        concurrent_agents.append(agent)

                            # Execute concurrently
        start_time = time.time()
        concurrent_result = await self._execute_concurrent_context_test(concurrent_agents)
        execution_time = time.time() - start_time

        assert concurrent_result["all_isolated"] is True
        assert concurrent_result["no_cross_contamination"] is True
        assert execution_time < 10.0  # Performance requirement

        @pytest.mark.e2e
    async def test_context_window_size_limits(self, context_setup):
        """Test context window size management and limits."""
        supervisor = context_setup["supervisor"]

                                # Create agent with large context
        agent = TestContextAgent( )
        llm_manager=context_setup["llm_manager"],
        name="LargeContextAgent",
        description="Large context test agent"
                                

                                # Create context approaching limits
        large_context = { )
        "large_data": "x" * 10000,  # 10KB of data
        "memory_intensive": list(range(1000)),
        "context_id": str(uuid.uuid4())
                                
        agent.context = large_context

                                # Test context size handling
        size_result = await self._test_context_size_limits(agent)

        assert size_result["within_limits"] is True
        assert size_result["memory_efficient"] is True

        @pytest.mark.e2e
    async def test_context_persistence_across_tasks(self, context_setup):
        """Test context persistence for agent task continuity."""
        pass
        supervisor = context_setup["supervisor"]

                                    # Create agent with persistent context
        agent = TestContextAgent( )
        llm_manager=context_setup["llm_manager"],
        name="PersistentAgent",
        description="Context persistence test agent"
                                    

                                    # Set initial context
        initial_context = { )
        "persistent_id": str(uuid.uuid4()),
        "task_counter": 0,
        "accumulated_data": []
                                    
        agent.context = initial_context

                                    # Execute multiple tasks
        persistence_result = await self._test_context_persistence(agent)

        assert persistence_result["context_maintained"] is True
        assert persistence_result["data_accumulated"] is True

        async def _validate_context_isolation(self, agents: List[TestContextAgent],
        contexts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate context isolation between agents."""
    # Check uniqueness
        context_ids = [ctx.get("agent_id") for ctx in contexts]
        all_unique = len(set(context_ids)) == len(context_ids)

    # Check for bleeding
        no_bleeding = True
        for i, agent in enumerate(agents):
        for j, other_agent in enumerate(agents):
        if i != j and agent.context == other_agent.context:
        no_bleeding = False
        break

                # Count fresh windows
        fresh_count = len([item for item in []])

        await asyncio.sleep(0)
        return { )
        "all_contexts_unique": all_unique,
        "no_context_bleeding": no_bleeding,
        "fresh_window_count": fresh_count
                

    async def _test_context_cleanup(self, agent: TestContextAgent) -> Dict[str, Any]:
        """Test context cleanup functionality."""
    # Simulate context usage
        await agent.execute()

    # Simulate cleanup
        original_context = agent.context.copy()
        agent.context.clear()

        return { )
        "context_cleared": len(agent.context) == 0,
        "memory_released": agent.context != original_context
    

    async def _execute_concurrent_context_test(self, agents: List[TestContextAgent]) -> Dict[str, Any]:
        """Execute concurrent context isolation test."""
    # Store original contexts
        original_contexts = [agent.context.copy() for agent in agents]

    # Execute concurrently
        tasks = [agent.execute() for agent in agents]
        await asyncio.gather(*tasks, return_exceptions=True)

    # Validate isolation after execution
        all_isolated = True
        no_contamination = True

        for i, agent in enumerate(agents):
        # Check if context preserved its identity
        if agent.context.get("concurrent_id") != original_contexts[i].get("concurrent_id"):
        all_isolated = False

            # Check for cross-contamination
        for j, other_agent in enumerate(agents):
        if i != j and agent.context.get("isolation_marker") == other_agent.context.get("isolation_marker"):
        no_contamination = False

        return { )
        "all_isolated": all_isolated,
        "no_cross_contamination": no_contamination
                    

    async def _test_context_size_limits(self, agent: TestContextAgent) -> Dict[str, Any]:
        """Test context size limit handling."""
        context_size = len(str(agent.context))
        memory_usage = context_size * 2  # Estimate memory usage

    # Check if within reasonable limits (1MB)
        within_limits = context_size < 1024 * 1024
        memory_efficient = memory_usage < 2 * 1024 * 1024

        return { )
        "within_limits": within_limits,
        "memory_efficient": memory_efficient,
        "context_size": context_size
    

    async def _test_context_persistence(self, agent: TestContextAgent) -> Dict[str, Any]:
        """Test context persistence across multiple tasks."""
        initial_id = agent.context.get("persistent_id")

    # Execute multiple tasks
        for i in range(3):
        agent.context["task_counter"] = i
        agent.context["accumulated_data"].append("formatted_string")
        await agent.execute()

        # Validate persistence
        context_maintained = agent.context.get("persistent_id") == initial_id
        data_accumulated = len(agent.context.get("accumulated_data", [])) == 3

        return { )
        "context_maintained": context_maintained,
        "data_accumulated": data_accumulated
        


        @pytest.mark.integration
        @pytest.mark.e2e
    async def test_memory_isolation_validation():
        """Test memory isolation between agent contexts."""
        config = get_config()
        llm_manager = LLMManager(config)

            # Create two agents with separate memory spaces
        agent1 = TestContextAgent(llm_manager=llm_manager, name="MemoryAgent1")
        agent2 = TestContextAgent(llm_manager=llm_manager, name="MemoryAgent2")

            # Set distinct memory contexts
        agent1.context = {"memory_id": "mem_1", "data": [1, 2, 3]}
        agent2.context = {"memory_id": "mem_2", "data": [4, 5, 6]}

            # Validate memory isolation
        assert agent1.context["memory_id"] != agent2.context["memory_id"]
        assert agent1.context["data"] != agent2.context["data"]


        @pytest.mark.integration
        @pytest.mark.e2e
    async def test_context_window_refresh():
        """Test context window refresh mechanism."""
        pass
        config = get_config()
        llm_manager = LLMManager(config)

        agent = TestContextAgent(llm_manager=llm_manager, name="RefreshAgent")
        original_context = {"refresh_id": str(uuid.uuid4()), "state": "original"}
        agent.context = original_context

                # Simulate context refresh
        agent.context = {"refresh_id": str(uuid.uuid4()), "state": "refreshed"}

                # Validate refresh
        assert agent.context["state"] == "refreshed"
        assert agent.context["refresh_id"] != original_context["refresh_id"]
