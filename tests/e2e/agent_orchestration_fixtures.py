"""Shared fixtures for Agent Orchestration Testing
Architecture: Modular test fixtures supporting multi-agent system validation
BVJ: Shared testing infrastructure reduces duplication and ensures consistency

COMPLIANCE: Updated per CLAUDE.md requirements
- MOCKS ARE FORBIDDEN in e2e tests
- Must use REAL services (LLM, databases, agents)
- Absolute imports only
"""

import uuid
import asyncio
from datetime import datetime, timezone
from typing import Any, Dict

import pytest

# Absolute imports per CLAUDE.md import_management_architecture.xml
from tests.e2e.config import CustomerTier


# REMOVED: mock_supervisor_agent deprecated fixture per CLAUDE.md
# Use real_supervisor_agent instead for e2e testing


@pytest.fixture
async def real_supervisor_agent():
    """Real supervisor agent for E2E orchestration testing - COMPLIANCE with CLAUDE.md
    Uses REAL services, NO MOCKS allowed in e2e tests
    """
    # Absolute imports per CLAUDE.md requirements
    from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
    from netra_backend.app.dependencies import get_db_session
    from netra_backend.app.llm.llm_manager import LLMManager
    from netra_backend.app.websocket_core import get_websocket_manager
    from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
    from netra_backend.app.config import get_config
    
    # Use REAL services - no mocks allowed per CLAUDE.md
    config = get_config()
    
    # Get real database session - handle async generator properly
    db_session_gen = get_db_session()
    db_session = await db_session_gen.__anext__()
    
    # Create real LLM manager (will use actual LLM service)
    llm_manager = LLMManager(settings=config)
    
    # Get real websocket manager
    websocket_manager = get_websocket_manager()
    
    # Create real tool dispatcher
    tool_dispatcher = ToolDispatcher()  # ToolDispatcher takes tools list, not these params
    
    # Create REAL supervisor agent with REAL dependencies
    supervisor = SupervisorAgent(
        db_session=db_session,
        llm_manager=llm_manager, 
        websocket_manager=websocket_manager,
        tool_dispatcher=tool_dispatcher
    )
    
    return supervisor


# REMOVED: mock_sub_agents deprecated fixture per CLAUDE.md  
# Use real_sub_agents instead for e2e testing


@pytest.fixture
async def real_sub_agents():
    """Real sub-agents for E2E coordination testing - COMPLIANCE with CLAUDE.md
    Uses REAL agent instances, NO MOCKS allowed in e2e tests
    """
    # Absolute imports per CLAUDE.md requirements - using actual available agents
    from netra_backend.app.agents.data_sub_agent import DataSubAgent
    from netra_backend.app.agents.optimizations_core_sub_agent import OptimizationsCoreSubAgent
    from netra_backend.app.agents.actions_to_meet_goals_sub_agent import ActionsToMeetGoalsSubAgent
    from netra_backend.app.agents.reporting_sub_agent import ReportingSubAgent
    from netra_backend.app.dependencies import get_db_session
    from netra_backend.app.llm.llm_manager import LLMManager
    from netra_backend.app.websocket_core import get_websocket_manager
    from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
    from netra_backend.app.config import get_config
    
    # Use REAL services - no mocks allowed per CLAUDE.md
    config = get_config()
    
    # Get real services - handle async generator properly
    db_session_gen = get_db_session()
    db_session = await db_session_gen.__anext__()
    
    llm_manager = LLMManager(settings=config)
    websocket_manager = get_websocket_manager()
    tool_dispatcher = ToolDispatcher()  # ToolDispatcher takes tools list, not these params
    
    # Create REAL agent instances using actual available agents
    agents = {}
    
    # TESTS MUST RAISE ERRORS - NO TRY-EXCEPT per CLAUDE.md
    agents["data"] = DataSubAgent(
        llm_manager=llm_manager,
        tool_dispatcher=tool_dispatcher,
        websocket_manager=websocket_manager
    )
    
    # TESTS MUST RAISE ERRORS - NO TRY-EXCEPT per CLAUDE.md
    agents["optimizations"] = OptimizationsCoreSubAgent(
        llm_manager=llm_manager,
        tool_dispatcher=tool_dispatcher,
        websocket_manager=websocket_manager
    )
    
    # TESTS MUST RAISE ERRORS - NO TRY-EXCEPT per CLAUDE.md
    agents["actions"] = ActionsToMeetGoalsSubAgent(
        llm_manager=llm_manager,
        tool_dispatcher=tool_dispatcher
    )
        
    # TESTS MUST RAISE ERRORS - NO TRY-EXCEPT per CLAUDE.md
    agents["reporting"] = ReportingSubAgent(
        llm_manager=llm_manager,
        tool_dispatcher=tool_dispatcher,
        websocket_manager=websocket_manager
    )
    
    return agents


@pytest.fixture
def sample_agent_state():
    """Sample agent state for testing - REAL DeepAgentState object per CLAUDE.md"""
    # Import the proper DeepAgentState class
    from netra_backend.app.agents.state import DeepAgentState
    
    # Create a REAL DeepAgentState object using proper constructor parameters
    state = DeepAgentState(
        user_request="Optimize AI costs for Q4",
        user_id=str(uuid.uuid4()),
        run_id=str(uuid.uuid4()),
        chat_thread_id=str(uuid.uuid4()),
        agent_input={"tier": CustomerTier.ENTERPRISE.value, "monthly_spend": 50000}
    )
    
    return state


# REMOVED: websocket_mock deprecated fixture per CLAUDE.md
# Use real_websocket instead for e2e testing


@pytest.fixture
async def real_websocket():
    """Real WebSocket connection for E2E streaming response testing - COMPLIANCE with CLAUDE.md
    Uses REAL WebSocket connection, NO MOCKS
    """
    import aiohttp
    from tests.e2e.config import TEST_ENDPOINTS
    
    session = aiohttp.ClientSession()
    ws_url = TEST_ENDPOINTS.ws_url
    
    # TESTS MUST RAISE ERRORS - NO TRY-EXCEPT per CLAUDE.md
    # Create REAL WebSocket connection to actual service
    ws = await session.ws_connect(ws_url)
    yield ws
    # Cleanup - but must raise errors if cleanup fails
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