"""
Pytest configuration for ClickHouse tests
Provides fixtures and test configuration
"""

import asyncio
import os
import sys
from unittest.mock import AsyncMock, MagicMock

import pytest

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))


# Remove event_loop fixture to prevent conflicts with pytest-asyncio auto mode
# config/pytest.ini has asyncio_mode = auto which handles event loops automatically


@pytest.fixture
def mock_clickhouse_client():
    """Mock ClickHouse client for testing"""
    client = AsyncMock()
    client.execute = AsyncMock(return_value=[])
    client.execute_query = AsyncMock(return_value=[])
    client.command = AsyncMock(return_value=None)
    client.insert_data = AsyncMock(return_value=None)
    client.test_connection = AsyncMock(return_value=True)
    client.disconnect = AsyncMock()
    return client


@pytest.fixture
def mock_db_session():
    """Mock database session"""
    session = MagicMock()
    session.add = MagicMock()
    session.commit = MagicMock()
    session.refresh = MagicMock()
    session.delete = MagicMock()
    session.query = MagicMock()
    return session


@pytest.fixture
def sample_corpus_data():
    """Sample corpus data for testing"""
    return {
        "simple_chat": [
            ("Hello, how are you?", "I'm doing well, thank you!"),
            ("What's the weather?", "I don't have access to weather data.")
        ],
        "rag_pipeline": [
            ("Find information about Python", "Python is a high-level programming language..."),
            ("Search for ML algorithms", "Machine learning algorithms include...")
        ],
        "tool_use": [
            ("Calculate 2+2", "The result is 4"),
            ("Get current time", "The current time is 12:00 PM")
        ]
    }


@pytest.fixture
def sample_corpus_records():
    """Sample corpus records for validation testing"""
    return [
        {
            "workload_type": "simple_chat",
            "prompt": "Test prompt",
            "response": "Test response",
            "metadata": {"test": True}
        },
        {
            "workload_type": "rag_pipeline",
            "prompt": "Another prompt",
            "response": "Another response",
            "metadata": {"index": 1}
        }
    ]


@pytest.fixture
def mock_redis_manager():
    """Mock Redis manager for caching tests"""
    manager = MagicMock()
    manager.enabled = True
    manager.get = AsyncMock(return_value=None)
    manager.set = AsyncMock(return_value=True)
    return manager


@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """Set up test environment variables"""
    monkeypatch.setenv("ENVIRONMENT", "testing")
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")
    monkeypatch.setenv("CLICKHOUSE_URL", "clickhouse://test:test@localhost:9000/test")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key")


@pytest.fixture
def performance_metrics_data():
    """Sample performance metrics data"""
    return {
        "user_id": 123,
        "workload_id": "wl_test",
        "metrics": {
            "latency_ms": [100, 150, 200, 250, 300],
            "throughput": [1000, 1200, 800, 900, 1100],
            "cost_cents": [10, 12, 8, 9, 11]
        },
        "timestamps": [
            "2025-01-01T10:00:00",
            "2025-01-01T10:01:00",
            "2025-01-01T10:02:00",
            "2025-01-01T10:03:00",
            "2025-01-01T10:04:00"
        ]
    }


@pytest.fixture
def anomaly_detection_data():
    """Sample data for anomaly detection testing"""
    return {
        "baseline_values": [100, 102, 98, 101, 99, 103, 97, 100, 102, 98],
        "anomaly_values": [100, 102, 500, 101, 99],  # 500 is anomaly
        "metric_name": "latency_ms",
        "z_score_threshold": 2.0
    }


def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "clickhouse: mark test as requiring ClickHouse"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )