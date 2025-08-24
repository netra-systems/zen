"""
Helper functions for core infrastructure tests.
Provides reusable setup, assertions, and mock creation.
Security and logging helpers moved to core_test_security_helpers.py to maintain 450-line limit.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, Mock, patch

from cryptography.fernet import Fernet

def create_mock_config():
    """Create a mock configuration object with all required fields."""
    # Mock: Generic component isolation for controlled unit testing
    config = Mock()
    _set_basic_config_fields(config)
    _set_service_configs(config)
    _set_auth_configs(config)
    
    return config

def _set_basic_config_fields(config):
    """Set basic configuration fields."""
    config.environment = "production"
    config.database_url = "postgresql://user:pass@localhost/db"
    config.jwt_secret_key = "a" * 32
    config.fernet_key = Fernet.generate_key()

def _set_service_configs(config):
    """Set service configuration fields."""
    # Mock: ClickHouse external database isolation for unit testing performance
    config.clickhouse_logging = Mock(enabled=True)
    # Mock: ClickHouse external database isolation for unit testing performance
    config.clickhouse_native = Mock(host="localhost", password="pass")
    # Mock: ClickHouse external database isolation for unit testing performance
    config.clickhouse_https = Mock(host="localhost", password="pass")
    # Mock: Redis caching isolation to prevent test interference and external dependencies
    config.redis = Mock(host="localhost", password="pass")

def _set_auth_configs(config):
    """Set authentication configuration fields."""
    # Mock: Component isolation for controlled unit testing
    config.oauth_config = Mock(client_id="id", client_secret="secret")
    config.llm_configs = {
        # Mock: OpenAI API isolation for testing without external service dependencies
        "default": Mock(api_key="key", model_name="model", provider="openai")
    }
    # Mock: Component isolation for controlled unit testing
    config.langfuse = Mock(secret_key="key", public_key="pub")

def create_failing_async_func(fail_count: int, success_result: str = "success"):
    """Create async function that fails N times then succeeds."""
    call_count = [0]
    failing_func = _create_failing_func(call_count, fail_count, success_result)
    return failing_func, lambda: call_count[0]

def create_mock_database():
    """Create a mock database with standard methods."""
    # Mock: Generic component isolation for controlled unit testing
    mock_db = AsyncMock()
    _setup_mock_database_results(mock_db)
    
    return mock_db

def _setup_mock_database_results(mock_db):
    """Setup mock database return values."""
    mock_db.execute.return_value.fetchall.return_value = [
        ("users", "id", "integer"),
        ("users", "email", "varchar"),
    ]
    mock_db.execute.return_value.scalar.return_value = 1

def create_log_record(name: str, level: int, message: str):
    """Create a log record for testing formatters."""
    log_params = _create_log_record_params(name, level, message)
    return logging.LogRecord(**log_params)

def _create_log_record_params(name: str, level: int, message: str):
    """Create parameters for log record."""
    return {
        'name': name, 'level': level, 'pathname': "test.py",
        'lineno': 10, 'msg': message, 'args': (), 'exc_info': None
    }

def assert_json_log_format(formatted_log: str, expected_fields: List[str]):
    """Assert that log is valid JSON with expected fields."""
    data = json.loads(formatted_log)
    for field in expected_fields:
        assert field in data

def create_mock_services_dict():
    """Create mock services dictionary for health checks."""
    return {
        "redis": {"host": "localhost", "port": 6379},
        "clickhouse": {"host": "localhost", "port": 9000}
    }

def create_schema_comparison_data():
    """Create test data for schema comparison."""
    expected_schema = _create_expected_schema()
    actual_schema = _create_actual_schema_with_differences()
    return expected_schema, actual_schema

def _create_failing_func(call_count, fail_count, success_result):
    """Create the actual failing function."""
    async def failing_func():
        call_count[0] += 1
        if call_count[0] < fail_count:
            raise ConnectionError("Transient error")
        return success_result
    return failing_func

def _create_expected_schema():
    """Create expected schema for comparison."""
    return {
        "users": ["id", "email", "created_at"],
        "posts": ["id", "user_id", "content"]
    }

def _create_actual_schema_with_differences():
    """Create actual schema with intentional differences."""
    return {
        "users": ["id", "email"],  # Missing created_at
        "posts": ["id", "user_id", "content", "deleted"]  # Extra column
    }

def _assert_table_field_changes(changes, expected_missing, expected_extra):
    """Assert table field changes are correct."""
    _assert_missing_fields(changes, expected_missing)
    _assert_extra_fields(changes, expected_extra)

def assert_schema_diff_results(diff: Dict, expected_missing: List[str], expected_extra: List[str]):
    """Assert schema diff contains expected differences."""
    for table, changes in diff.items():
        _assert_table_field_changes(changes, expected_missing, expected_extra)

def _assert_missing_fields(changes: Dict, expected_missing: List[str]):
    """Assert missing fields are correctly identified."""
    if "missing" in changes and expected_missing:
        for field in expected_missing:
            assert field in changes["missing"]

def _assert_extra_fields(changes: Dict, expected_extra: List[str]):
    """Assert extra fields are correctly identified."""
    if "extra" in changes and expected_extra:
        for field in expected_extra:
            assert field in changes["extra"]

# Security and logging helpers moved to core_test_security_helpers.py
from netra_backend.tests.helpers.core_test_security_helpers import (
    assert_service_categorization,
    create_mock_secret_manager_with_rotation,
    create_startup_check_results,
    create_unified_logger_with_context,
)
