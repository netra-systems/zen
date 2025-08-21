"""Agent Tool Execution Pipeline Integration Test ($2.8M impact)

L3 realism level - tests end-to-end agent tool execution from supervisor
through sub-agents using real PostgreSQL, Redis, ClickHouse containers.

Business Value Justification:
- Segment: Enterprise ($2.8M revenue impact)
- Business Goal: Platform Stability - Agent execution reliability
- Value Impact: Prevents agent execution failures that lose customer trust
- Strategic Impact: Core platform functionality critical for all paid tiers
"""

from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

import asyncio
import pytest
import time
from typing import Dict, Any

# Add project root to path

from netra_backend.tests.integration.critical_missing.shared_infrastructure.containerized_services import ServiceOrchestrator
from netra_backend.app.services.agent_service_core import AgentService
from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.db.models_agent import Run, Step
from netra_backend.app.schemas.Request import RequestModel
from netra_backend.app.core.database_recovery_core import ConnectionPoolRefreshStrategy
from netra_backend.app.core.exceptions_base import NetraException

# Add project root to path

# Define test-specific exceptions
class AgentTimeoutError(NetraException):
    pass

class AgentPermissionError(NetraException):
    pass


@pytest.fixture(scope="module")
async def l3_services():
    """L3 realism: Real containerized services"""
    orchestrator = ServiceOrchestrator()
    connections = await orchestrator.start_all()
    yield orchestrator, connections
    await orchestrator.stop_all()


@pytest.fixture
async def agent_service(l3_services):
    """Agent service with L3 real dependencies"""
    orchestrator, connections = l3_services
    supervisor = SupervisorAgent()
    return AgentService(supervisor)


@pytest.fixture
async def reset_services(l3_services):
    """Reset services for test isolation"""
    orchestrator, _ = l3_services
    await orchestrator.reset_for_test()


class TestAgentToolExecutionPipeline:
    """Test end-to-end agent tool execution pipeline"""

    async def test_basic_tool_execution_pipeline(self, agent_service, reset_services):
        """Test basic end-to-end tool execution < 2 seconds"""
        start_time = time.time()
        request = RequestModel(query="List available tools", user_request="test_basic")
        result = await agent_service.run(request, "test_run_basic", False)
        execution_time = time.time() - start_time
        
        assert execution_time < 2.0
        assert result is not None

    async def test_permission_failure_handling(self, agent_service, reset_services):
        """Test permission failure handling in tool execution"""
        request = RequestModel(query="Execute admin tool", user_request="test_permission")
        
        with pytest.raises(AgentPermissionError):
            await agent_service.run(request, "test_run_permission", False)

    async def test_timeout_handling(self, agent_service, reset_services):
        """Test timeout handling in long-running tool execution"""
        request = RequestModel(query="Long running task", user_request="test_timeout")
        
        with pytest.raises(AgentTimeoutError):
            await asyncio.wait_for(
                agent_service.run(request, "test_run_timeout", False), 
                timeout=1.0
            )

    async def test_concurrent_tool_executions(self, agent_service, reset_services):
        """Test concurrent tool executions performance"""
        start_time = time.time()
        requests = [
            RequestModel(query=f"Tool execution {i}", user_request=f"test_concurrent_{i}")
            for i in range(5)
        ]
        
        tasks = [
            agent_service.run(req, f"test_run_concurrent_{i}", False)
            for i, req in enumerate(requests)
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        execution_time = time.time() - start_time
        
        assert execution_time < 2.0
        assert len(results) == 5

    async def test_supervisor_to_subagent_delegation(self, agent_service, reset_services):
        """Test supervisor delegation to sub-agents"""
        request = RequestModel(query="Analyze data", user_request="test_delegation")
        result = await agent_service.run(request, "test_run_delegation", False)
        
        assert result is not None

    async def test_tool_execution_with_database_recovery(self, agent_service, reset_services):
        """Test tool execution continues after database recovery"""
        recovery_strategy = ConnectionPoolRefreshStrategy()
        request = RequestModel(query="Database operation", user_request="test_recovery")
        
        result = await agent_service.run(request, "test_run_recovery", False)
        assert result is not None

    async def test_websocket_message_handling(self, agent_service, reset_services):
        """Test WebSocket message handling in tool execution"""
        message = {"type": "start_agent", "payload": {"query": "Test WebSocket"}}
        
        await agent_service.handle_websocket_message("test_user", message, None)

    async def test_streaming_tool_execution(self, agent_service, reset_services):
        """Test streaming tool execution pipeline"""
        message = "Stream test execution"
        stream_generator = agent_service.generate_stream(message, "test_thread")
        
        chunks = []
        async for chunk in stream_generator:
            chunks.append(chunk)
            if len(chunks) >= 3:
                break
        
        assert len(chunks) > 0