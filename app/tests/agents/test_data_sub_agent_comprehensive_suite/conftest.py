"""
Shared fixtures and test configuration for DataSubAgent comprehensive tests
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from app.agents.data_sub_agent.agent import DataSubAgent


@pytest.fixture
def mock_dependencies():
    """Create mock dependencies for DataSubAgent"""
    mock_llm_manager = Mock()
    mock_tool_dispatcher = Mock()
    return mock_llm_manager, mock_tool_dispatcher


@pytest.fixture
def agent(mock_dependencies):
    """Create DataSubAgent instance with mocked dependencies"""
    mock_llm_manager, mock_tool_dispatcher = mock_dependencies
    with patch('app.agents.data_sub_agent.data_sub_agent_core.RedisManager') as mock_redis_class:
        # Setup proper async mocks for redis operations
        mock_redis_instance = Mock()
        mock_redis_instance.get = AsyncMock()
        mock_redis_instance.set = AsyncMock()
        mock_redis_instance.delete = AsyncMock()
        mock_redis_instance.exists = AsyncMock()
        mock_redis_class.return_value = mock_redis_instance
        
        agent = DataSubAgent(mock_llm_manager, mock_tool_dispatcher)
        # Ensure redis_manager is properly mocked
        if hasattr(agent, 'redis_manager') and agent.redis_manager:
            agent.redis_manager.get = AsyncMock()
            agent.redis_manager.set = AsyncMock()
    return agent


@pytest.fixture
def sample_performance_data():
    """Sample performance metrics data for testing"""
    return [
        {
            'time_bucket': '2024-01-01T12:00:00',
            'event_count': 100,
            'latency_p50': 50.0,
            'latency_p95': 95.0,
            'latency_p99': 99.0,
            'avg_throughput': 1000.0,
            'peak_throughput': 2000.0,
            'error_rate': 0.5,
            'total_cost': 10.0,
            'unique_workloads': 5
        }
    ]


@pytest.fixture
def sample_anomaly_data():
    """Sample anomaly detection data for testing"""
    return [
        {
            'timestamp': '2024-01-01T12:00:00',
            'value': 50.0,
            'avg_value': 50.0,
            'std_value': 10.0,
            'z_score': 0.0
        },
        {
            'timestamp': '2024-01-01T12:01:00',
            'value': 100.0,
            'avg_value': 50.0,
            'std_value': 10.0,
            'z_score': 5.0
        }
    ]


@pytest.fixture
def sample_usage_patterns():
    """Sample usage pattern data for testing"""
    return [
        {'day_of_week': 1, 'hour': 9, 'total_events': 1000, 'avg_latency': 50.0},
        {'day_of_week': 1, 'hour': 10, 'total_events': 1500, 'avg_latency': 45.0},
        {'day_of_week': 1, 'hour': 11, 'total_events': 2000, 'avg_latency': 55.0}
    ]