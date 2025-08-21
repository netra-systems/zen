"""Shared fixtures for Agent Orchestration Testing
Architecture: Modular test fixtures supporting multi-agent system validation
BVJ: Shared testing infrastructure reduces duplication and ensures consistency
"""

import pytest
import uuid
from typing import Dict, Any
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone

from netra_backend.tests.unified.config import TestTier


@pytest.fixture
def mock_supervisor_agent():
    """Mock supervisor agent for orchestration testing"""
    supervisor = MagicMock()
    supervisor.route_request = AsyncMock()
    supervisor.execute_pipeline = AsyncMock() 
    supervisor.handle_agent_failure = AsyncMock()
    supervisor.get_health_status = MagicMock(return_value={"status": "healthy"})
    supervisor.get_performance_metrics = MagicMock(return_value={})
    supervisor.get_resource_metrics = MagicMock(return_value={})
    return supervisor


@pytest.fixture
def mock_sub_agents():
    """Mock sub-agents for coordination testing"""
    return {
        "data": MagicMock(execute=AsyncMock(), name="DataSubAgent"),
        "optimizations": MagicMock(execute=AsyncMock(), name="OptimizationsSubAgent"), 
        "actions": MagicMock(execute=AsyncMock(), name="ActionsSubAgent"),
        "reporting": MagicMock(execute=AsyncMock(), name="ReportingSubAgent")
    }


@pytest.fixture
def sample_agent_state():
    """Sample agent state for testing"""
    return {
        "user_request": "Optimize AI costs for Q4",
        "user_id": str(uuid.uuid4()),
        "run_id": str(uuid.uuid4()),
        "tier": TestTier.ENTERPRISE.value,
        "context": {"monthly_spend": 50000}
    }


@pytest.fixture
def websocket_mock():
    """Mock WebSocket for streaming response testing"""
    ws = AsyncMock()
    ws.send_json = AsyncMock()
    ws.receive_text = AsyncMock()
    ws.close = AsyncMock()
    return ws


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