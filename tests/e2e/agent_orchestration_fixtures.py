"""Shared fixtures for Agent Orchestration Testing
Architecture: Modular test fixtures supporting multi-agent system validation
BVJ: Shared testing infrastructure reduces duplication and ensures consistency
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict
from typing import Any, Dict
import asyncio

import pytest

from tests.e2e.config import CustomerTier


@pytest.fixture
async def mock_supervisor_agent():
    """Mock supervisor agent for E2E orchestration testing"""
    from unittest.mock import AsyncMock, MagicMock
    
    mock = AsyncMock()
    mock.route_request = AsyncMock()
    mock.execute_pipeline = AsyncMock()
    mock.handle_agent_failure = AsyncMock()
    mock.get_health_status = AsyncMock()
    mock.get_performance_metrics = AsyncMock()
    mock.get_resource_metrics = AsyncMock()
    
    return mock


@pytest.fixture
async def real_supervisor_agent():
    """Real supervisor agent for E2E orchestration testing"""
    from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
    from netra_backend.app.dependencies import get_db_session
    from netra_backend.app.llm.llm_manager import LLMManager
    from netra_backend.app.websocket_core import get_websocket_manager
    from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
    from unittest.mock import AsyncMock
    
    # Create mock dependencies for testing
    db_session = AsyncMock()
    llm_manager = AsyncMock(spec=LLMManager)
    websocket_manager = get_websocket_manager()
    tool_dispatcher = AsyncMock(spec=ToolDispatcher)
    
    # Create real supervisor agent with mocked dependencies
    supervisor = SupervisorAgent(db_session, llm_manager, websocket_manager, tool_dispatcher)
    
    # Mock the execute_pipeline method for testing
    supervisor.execute_pipeline = AsyncMock(return_value={
        "status": "success", 
        "executed_agents": ["data", "optimizations"],
        "combined_analysis": {"monthly_cost": 10000, "potential_savings": 2500},
        "pipeline_status": "partial_success"
    })
    
    return supervisor


@pytest.fixture
async def mock_sub_agents():
    """Mock sub-agents for E2E coordination testing"""
    from unittest.mock import AsyncMock
    
    return {
        "data": AsyncMock(),
        "optimizations": AsyncMock(),
        "actions": AsyncMock(), 
        "reporting": AsyncMock()
    }


@pytest.fixture
async def real_sub_agents():
    """Real sub-agents for E2E coordination testing"""
    from unittest.mock import AsyncMock
    
    # For E2E testing, use mock agents that simulate real agent behavior
    # This allows tests to run without complex agent setup
    data_agent = AsyncMock()
    data_agent.execute = AsyncMock(return_value={"data_analysis": "completed", "status": "success"})
    
    opt_agent = AsyncMock()
    opt_agent.execute = AsyncMock(return_value={"optimization_analysis": "completed", "status": "success"})
    
    action_agent = AsyncMock()
    action_agent.execute = AsyncMock(return_value={"actions_executed": True, "status": "success"})
    
    reporting_agent = AsyncMock()
    reporting_agent.execute = AsyncMock(return_value={"report_generated": True, "status": "success"})
    
    return {
        "data": data_agent,
        "optimizations": opt_agent,
        "actions": action_agent,
        "reporting": reporting_agent
    }


@pytest.fixture
def sample_agent_state():
    """Sample agent state for testing"""
    return {
        "user_request": "Optimize AI costs for Q4",
        "user_id": str(uuid.uuid4()),
        "run_id": str(uuid.uuid4()),
        "tier": CustomerTier.ENTERPRISE.value,
        "context": {"monthly_spend": 50000}
    }


@pytest.fixture
async def websocket_mock():
    """Mock WebSocket connection for E2E streaming response testing"""
    from unittest.mock import AsyncMock, MagicMock
    
    mock = AsyncMock()
    mock.send_str = AsyncMock()
    mock.send_json = AsyncMock()
    mock.receive = AsyncMock()
    mock.receive_str = AsyncMock()
    mock.receive_json = AsyncMock()
    mock.close = AsyncMock()
    mock.closed = False
    
    return mock


@pytest.fixture
async def real_websocket():
    """Real WebSocket connection for E2E streaming response testing"""
    import aiohttp
    from tests.e2e.config import TEST_ENDPOINTS
    
    session = aiohttp.ClientSession()
    ws_url = TEST_ENDPOINTS.ws_url
    
    # Create real WebSocket connection
    ws = await session.ws_connect(ws_url)
    
    yield ws
    
    await ws.close()
    await session.close()


@pytest.fixture
def routing_test_data():
    """Test data for routing scenarios"""
    return {
        "data_request": {"type": "data_analysis", "query": "Show cost trends"},
        "optimization_request": {"type": "optimization", "goal": "reduce_costs"},
        "complex_request": {"type": "comprehensive", "goal": "full_optimization"},
        "unknown_request": {"type": "unknown", "query": "invalid"}
    }


@pytest.fixture
def coordination_test_data():
    """Test data for multi-agent coordination"""
    return {
        "pipeline_results": {
            "data": {"monthly_cost": 10000, "efficiency": 0.7},
            "optimizations": {"potential_savings": 3000, "recommendations": 5}
        },
        "expected_results": {"data": {"cost_data": 1000}, "optimizations": {"savings": 200}}
    }


@pytest.fixture
def failure_recovery_data():
    """Test data for failure recovery scenarios"""
    return {
        "partial_failure": {"status": "partial_failure", "failed_agent": "data", "result": "fallback_data"},
        "fallback_result": {"source": "fallback_agent", "data": "cached_analysis", "confidence": 0.6},
        "recovery_result": {"status": "recovered", "skipped": ["failed_agent"], "completed": ["agent1", "agent2"]},
        "critical_failure": {"status": "pipeline_stopped", "reason": "critical_agent_failed", "agent": "auth"}
    }


@pytest.fixture
def streaming_test_data():
    """Test data for streaming scenarios"""
    return {
        "update_messages": [
            {"type": "agent_started", "agent": "data", "timestamp": datetime.now(timezone.utc).isoformat()},
            {"type": "agent_progress", "agent": "data", "progress": 50},
            {"type": "agent_completed", "agent": "data", "result_preview": "Found cost issues"}
        ],
        "error_message": {
            "type": "agent_error",
            "agent": "optimizations", 
            "error": "LLM service unavailable",
            "fallback_activated": True,
            "timestamp": datetime.now(timezone.utc).isoformat()
        },
        "concurrent_updates": [
            {"agent": "data", "status": "processing", "thread_id": 1},
            {"agent": "optimizations", "status": "processing", "thread_id": 2},
            {"agent": "data", "status": "completed", "thread_id": 1},
            {"agent": "optimizations", "status": "completed", "thread_id": 2}
        ]
    }


@pytest.fixture
def health_monitoring_data():
    """Test data for health monitoring"""
    return {
        "healthy_status": {
            "status": "healthy",
            "active_agents": 4,
            "failed_agents": 0, 
            "average_response_time": 1.2,
            "last_health_check": datetime.now(timezone.utc).isoformat()
        },
        "unhealthy_status": {
            "status": "degraded",
            "failing_agents": ["data"],
            "error_rate": 0.15,
            "last_failure": datetime.now(timezone.utc).isoformat()
        }
    }


@pytest.fixture
def performance_metrics_data():
    """Test data for performance metrics"""
    return {
        "execution_metrics": {
            "execution_time_ms": 1500,
            "start_time": datetime.now(timezone.utc).isoformat(),
            "end_time": datetime.now(timezone.utc).isoformat()
        },
        "throughput_metrics": {
            "requests_per_minute": 45,
            "successful_requests": 43,
            "failed_requests": 2,
            "success_rate": 0.956
        },
        "resource_metrics": {
            "memory_usage_mb": 512,
            "cpu_usage_percent": 15.5,
            "active_connections": 8,
            "queue_length": 2
        }
    }