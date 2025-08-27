"""
Common fixtures and helpers for realistic ClickHouse operations tests
Shared utilities for production-like data volumes and patterns
"""

import json
import random
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock
from netra_backend.app.llm.llm_defaults import LLMModel, LLMConfig


import pytest

from netra_backend.app.db.clickhouse_query_fixer import (
    ClickHouseQueryInterceptor,
    fix_clickhouse_array_syntax,
    validate_clickhouse_query,
)

def generate_realistic_logs(count: int) -> List[Dict]:
    """Generate realistic log entries"""
    log_types = ["INFO", "WARNING", "ERROR", "DEBUG"]
    components = ["api", "worker", "scheduler", "llm_manager", "agent"]
    
    logs = []
    base_time = datetime.now() - timedelta(hours=1)
    
    for i in range(count):
        timestamp = base_time + timedelta(seconds=i * 0.1)
        logs.append({
            "timestamp": timestamp.isoformat(),
            "level": random.choice(log_types),
            "component": random.choice(components),
            "message": f"Log message {i}",
            "metadata": {
                "request_id": str(uuid.uuid4()),
                "user_id": random.randint(1, 100),
                "latency_ms": random.uniform(10, 500) if random.random() > 0.5 else None
            }
        })
    return logs

def generate_llm_metrics(count: int) -> List[Dict]:
    """Generate realistic LLM metrics"""
    models = [LLMModel.GEMINI_2_5_FLASH.value, LLMModel.GEMINI_2_5_FLASH.value, "claude-3", "gemini-pro"]
    
    metrics = []
    for i in range(count):
        metrics.append({
            "timestamp": datetime.now() - timedelta(minutes=count-i),
            "model": random.choice(models),
            "request_id": str(uuid.uuid4()),
            "input_tokens": random.randint(100, 2000),
            "output_tokens": random.randint(50, 1000),
            "latency_ms": random.uniform(500, 5000),
            "cost_cents": random.uniform(0.1, 5.0),
            "success": random.random() > 0.05,  # 95% success rate
            "temperature": random.choice([0.0, 0.3, 0.7, 1.0]),
            "user_id": random.randint(1, 50),
            "workload_type": random.choice(["chat", "completion", "embedding", "analysis"])
        })
    return metrics

def create_mock_clickhouse_client():
    """Create mock ClickHouse client for testing"""
    # Mock: Generic component isolation for controlled unit testing
    mock_client = AsyncMock()
    # Mock: Async component isolation for testing without real async operations
    mock_client.execute_query = AsyncMock(return_value=[{"result": "success"}])
    # Mock: Generic component isolation for controlled unit testing
    mock_client.execute = AsyncMock()
    return mock_client

def create_query_interceptor_with_mock():
    """Create query interceptor with mock client"""
    mock_client = create_mock_clickhouse_client()
    return ClickHouseQueryInterceptor(mock_client), mock_client

def validate_array_query_syntax(query: str) -> bool:
    """Validate that query uses proper ClickHouse array syntax"""
    # Check for incorrect array syntax patterns
    incorrect_patterns = [
        r'[a-zA-Z_][a-zA-Z0-9_.]*\[[^\]]*\]',  # field[index] pattern
        r'metrics\.(name|value|unit)\[',  # specific metrics array access
    ]
    
    for pattern in incorrect_patterns:
        import re
        if re.search(pattern, query):
            return False
    
    # Check for correct array functions
    correct_functions = ['arrayElement', 'arrayFirstIndex', 'arrayExists']
    has_correct_syntax = any(func in query for func in correct_functions)
    
    return has_correct_syntax or '[' not in query  # No arrays used is also valid

def get_sample_workload_event():
    """Get sample workload event for testing"""
    return {
        "event_id": str(uuid.uuid4()),
        "timestamp": datetime.now(),
        "user_id": random.randint(1, 100),
        "workload_id": "test_workload",
        "event_type": "request",
        "event_category": "llm_call",
        "dimensions": json.dumps({"test": True}),
        "metadata": json.dumps({"test_event": True})
    }

def get_sample_log_entry():
    """Get sample log entry for testing"""
    return {
        "timestamp": datetime.now().isoformat(),
        "level": "INFO",
        "component": "api",
        "message": "Test log message",
        "metadata": {
            "request_id": str(uuid.uuid4()),
            "user_id": 1,
            "latency_ms": 150.5
        }
    }

def get_performance_test_queries():
    """Get collection of performance test queries"""
    return {
        "simple_aggregation": """
            SELECT 
                workload_id,
                count() as request_count,
                avg(arrayElement(metrics.value, 
                    arrayFirstIndex(x -> x = 'latency_ms', metrics.name))) as avg_latency
            FROM workload_events
            WHERE timestamp >= now() - INTERVAL 1 HOUR
            GROUP BY workload_id
        """,
        "time_series": """
            SELECT 
                toStartOfMinute(timestamp) as minute,
                count() as events_per_minute,
                uniq(user_id) as unique_users
            FROM workload_events
            WHERE timestamp >= now() - INTERVAL 1 HOUR
            GROUP BY minute
            ORDER BY minute DESC
        """,
        "complex_join": """
            WITH llm_data AS (
                SELECT minute, avg_latency, total_cost
                FROM llm_metrics_hourly
            ),
            workload_data AS (
                SELECT minute, avg_throughput, error_rate
                FROM workload_metrics_hourly
            )
            SELECT l.*, w.*
            FROM llm_data l
            FULL OUTER JOIN workload_data w ON l.minute = w.minute
        """
    }

@pytest.fixture
def generate_realistic_logs_fixture():
    """Fixture for generating realistic logs"""
    return generate_realistic_logs

@pytest.fixture
def mock_clickhouse_client():
    """Fixture for mock ClickHouse client"""
    return create_mock_clickhouse_client()

@pytest.fixture
def query_interceptor_with_mock():
    """Fixture for query interceptor with mock client"""
    return create_query_interceptor_with_mock()

@pytest.fixture
def sample_workload_event():
    """Fixture for sample workload event"""
    return get_sample_workload_event()

@pytest.fixture
def sample_log_entry():
    """Fixture for sample log entry"""
    return get_sample_log_entry()

@pytest.fixture
def performance_queries():
    """Fixture for performance test queries"""
    return get_performance_test_queries()

@pytest.fixture
def llm_metrics_batch():
    """Fixture for batch of LLM metrics"""
    return generate_llm_metrics(100)