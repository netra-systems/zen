"""
Helper functions for core infrastructure tests.
Provides reusable setup, assertions, and mock creation.
"""

import json
import logging
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any, List
from datetime import datetime, timedelta
from cryptography.fernet import Fernet


def create_mock_config():
    """Create a mock configuration object with all required fields."""
    config = Mock()
    config.environment = "production"
    config.database_url = "postgresql://user:pass@localhost/db"
    config.jwt_secret_key = "a" * 32
    config.fernet_key = Fernet.generate_key()
    config.clickhouse_logging = Mock(enabled=True)
    config.clickhouse_native = Mock(host="localhost", password="pass")
    config.clickhouse_https = Mock(host="localhost", password="pass")
    config.clickhouse_https_dev = Mock(host="localhost", password="pass")
    config.oauth_config = Mock(client_id="id", client_secret="secret")
    config.llm_configs = {
        "default": Mock(api_key="key", model_name="model", provider="openai")
    }
    config.redis = Mock(host="localhost", password="pass")
    config.langfuse = Mock(secret_key="key", public_key="pub")
    return config


def create_failing_async_func(fail_count: int, success_result: str = "success"):
    """Create async function that fails N times then succeeds."""
    call_count = 0
    
    async def failing_func():
        nonlocal call_count
        call_count += 1
        if call_count < fail_count:
            raise ConnectionError("Transient error")
        return success_result
    
    return failing_func, lambda: call_count


def create_mock_database():
    """Create a mock database with standard methods."""
    mock_db = AsyncMock()
    mock_db.execute.return_value.fetchall.return_value = [
        ("users", "id", "integer"),
        ("users", "email", "varchar"),
    ]
    mock_db.execute.return_value.scalar.return_value = 1
    return mock_db


def create_log_record(name: str, level: int, message: str):
    """Create a log record for testing formatters."""
    return logging.LogRecord(
        name=name,
        level=level,
        pathname="test.py",
        lineno=10,
        msg=message,
        args=(),
        exc_info=None
    )


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
    expected_schema = {
        "users": ["id", "email", "created_at"],
        "posts": ["id", "user_id", "content"]
    }
    
    actual_schema = {
        "users": ["id", "email"],  # Missing created_at
        "posts": ["id", "user_id", "content", "deleted"]  # Extra column
    }
    
    return expected_schema, actual_schema


def assert_schema_diff_results(diff: Dict, expected_missing: List[str], expected_extra: List[str]):
    """Assert schema diff contains expected differences."""
    for table, changes in diff.items():
        if "missing" in changes and expected_missing:
            for field in expected_missing:
                assert field in changes["missing"]
        if "extra" in changes and expected_extra:
            for field in expected_extra:
                assert field in changes["extra"]


def create_mock_secret_manager_with_rotation():
    """Create secret manager that supports key rotation."""
    from cryptography.fernet import Fernet
    
    class MockSecretManager:
        def __init__(self, key):
            self.fernet = Fernet(key)
            self.old_keys = []
        
        def encrypt_secret(self, secret: str) -> str:
            return self.fernet.encrypt(secret.encode()).decode()
        
        def decrypt_secret(self, encrypted: str) -> str:
            try:
                return self.fernet.decrypt(encrypted.encode()).decode()
            except:
                # Try old keys for rotation support
                for old_fernet in self.old_keys:
                    try:
                        return old_fernet.decrypt(encrypted.encode()).decode()
                    except:
                        continue
                raise
        
        def rotate_key(self, new_key):
            self.old_keys.append(self.fernet)
            self.fernet = Fernet(new_key)
        
        def store_secrets(self, secrets: Dict, path: str):
            # Mock implementation
            pass
        
        def load_secrets(self, path: str) -> Dict:
            # Mock implementation
            return {"api_key": "secret_key_123", "db_password": "password_456"}
    
    return MockSecretManager


def create_unified_logger_with_context():
    """Create unified logger with context management."""
    class MockUnifiedLogger:
        def __init__(self):
            self.correlation_id = None
            self.context = {}
            self.logs = []
        
        def set_correlation_id(self, correlation_id: str):
            self.correlation_id = correlation_id
        
        def add_context(self, context: Dict):
            self.context.update(context)
        
        def log(self, level: str, message: str, **kwargs) -> Dict:
            log_entry = {
                "level": level,
                "message": message,
                "correlation_id": self.correlation_id,
                **self.context,
                **kwargs
            }
            self.logs.append(log_entry)
            return log_entry
        
        def get_aggregated_logs(self) -> List[Dict]:
            return self.logs
    
    return MockUnifiedLogger


def create_startup_check_results():
    """Create standard startup check results for testing."""
    return {
        "database": True,
        "auth": True,
        "cache": False,
        "metrics": False
    }


def assert_service_categorization(can_start: bool, critical_services: List[str]):
    """Assert that service categorization works correctly."""
    if all(service in ["database", "auth"] for service in critical_services):
        assert can_start  # Should start with critical services up