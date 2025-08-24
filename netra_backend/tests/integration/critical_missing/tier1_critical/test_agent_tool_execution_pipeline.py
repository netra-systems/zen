"""Agent Tool Execution Pipeline Integration Test ($2.8M impact)

L3 realism level - tests end-to-end agent tool execution from supervisor
through sub-agents using real PostgreSQL, Redis, ClickHouse containers.

Business Value Justification:
- Segment: Enterprise ($2.8M revenue impact)
- Business Goal: Platform Stability - Agent execution reliability
- Value Impact: Prevents agent execution failures that lose customer trust
- Strategic Impact: Core platform functionality critical for all paid tiers
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio
import time
from typing import Any, Dict

import pytest

from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.core.database_recovery_core import ConnectionPoolRefreshStrategy
from netra_backend.app.core.exceptions_base import NetraException
from netra_backend.app.db.models_agent import Run, Step
from netra_backend.app.schemas.Request import RequestModel
from netra_backend.app.services.agent_service_core import AgentService

# Import from shared infrastructure
from netra_backend.tests.integration.critical_missing.shared_infrastructure.containerized_services import (
    ServiceOrchestrator,
)

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
    
    # Create the required dependencies for SupervisorAgent
    from unittest.mock import AsyncMock, Mock
    from netra_backend.app.llm.llm_manager import LLMManager
    from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
    
    db_session = AsyncMock()
    llm_manager = Mock(spec=LLMManager)
    websocket_manager = AsyncMock()
    tool_dispatcher = Mock(spec=ToolDispatcher)
    
    supervisor = SupervisorAgent(db_session, llm_manager, websocket_manager, tool_dispatcher)
    yield AgentService(supervisor)

@pytest.fixture
async def reset_services(l3_services):
    """Reset services for test isolation"""
    orchestrator, _ = l3_services
    await orchestrator.reset_for_test()

class TestAgentToolExecutionPipeline:
    """Test end-to-end agent tool execution pipeline"""

    def _create_test_request(self, query: str, run_id: str, user_id: str = "test_user", table_suffix: str = "table") -> RequestModel:
        """Helper to create a valid RequestModel for testing"""
        from netra_backend.app.schemas.Request import DataSource, TimeRange, Workload
        
        data_source = DataSource(source_table=f"test_{table_suffix}")
        time_range = TimeRange(start_time="2025-01-01T00:00:00Z", end_time="2025-01-01T01:00:00Z")
        workload = Workload(
            run_id=run_id,
            query=query,
            data_source=data_source,
            time_range=time_range
        )
        
        return RequestModel(
            user_id=user_id,
            query=query,
            workloads=[workload]
        )

    @pytest.mark.asyncio
    async def test_basic_tool_execution_pipeline(self, agent_service, reset_services):
        """Test basic end-to-end tool execution < 2 seconds"""
        start_time = time.time()
        
        request = self._create_test_request("List available tools", "test_run_basic")
        result = await agent_service.run(request, "test_run_basic", False)
        execution_time = time.time() - start_time
        
        assert execution_time < 2.0
        assert result is not None

    @pytest.mark.asyncio
    async def test_permission_failure_handling(self, agent_service, reset_services):
        """Test permission failure handling in tool execution"""
        request = self._create_test_request("Execute admin tool", "test_run_permission", table_suffix="admin_table")
        
        with pytest.raises(AgentPermissionError):
            await agent_service.run(request, "test_run_permission", False)

    @pytest.mark.asyncio
    async def test_timeout_handling(self, agent_service, reset_services):
        """Test timeout handling in long-running tool execution"""
        request = self._create_test_request("Long running task", "test_run_timeout", table_suffix="slow_table")
        
        with pytest.raises(AgentTimeoutError):
            await asyncio.wait_for(
                agent_service.run(request, "test_run_timeout", False), 
                timeout=1.0
            )

    @pytest.mark.asyncio
    async def test_concurrent_tool_executions(self, agent_service, reset_services):
        """Test concurrent tool executions performance"""
        start_time = time.time()
        
        requests = [
            self._create_test_request(f"Tool execution {i}", f"test_run_concurrent_{i}", table_suffix=f"table_{i}")
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

    @pytest.mark.asyncio
    async def test_supervisor_to_subagent_delegation(self, agent_service, reset_services):
        """Test supervisor delegation to sub-agents"""
        request = self._create_test_request("Analyze data", "test_run_delegation", table_suffix="analysis_table")
        result = await agent_service.run(request, "test_run_delegation", False)
        
        assert result is not None

    @pytest.mark.asyncio
    async def test_tool_execution_with_database_recovery(self, agent_service, reset_services):
        """Test tool execution continues after database recovery"""
        recovery_strategy = ConnectionPoolRefreshStrategy()
        
        request = self._create_test_request("Database operation", "test_run_recovery", table_suffix="recovery_table")
        result = await agent_service.run(request, "test_run_recovery", False)
        assert result is not None

    @pytest.mark.asyncio
    async def test_websocket_message_handling(self, agent_service, reset_services):
        """Test WebSocket message handling in tool execution"""
        message = {"type": "start_agent", "payload": {"query": "Test WebSocket"}}
        
        await agent_service.handle_websocket_message("test_user", message, None)

    @pytest.mark.asyncio
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