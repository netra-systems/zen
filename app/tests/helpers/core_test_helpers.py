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
    config.clickhouse_logging = Mock(enabled=True)
    config.clickhouse_native = Mock(host="localhost", password="pass")
    config.clickhouse_https = Mock(host="localhost", password="pass")
    config.clickhouse_https_dev = Mock(host="localhost", password="pass")
    config.redis = Mock(host="localhost", password="pass")


def _set_auth_configs(config):
    """Set authentication configuration fields."""
    config.oauth_config = Mock(client_id="id", client_secret="secret")
    config.llm_configs = {
        "default": Mock(api_key="key", model_name="model", provider="openai")
    }
    config.langfuse = Mock(secret_key="key", public_key="pub")


def create_failing_async_func(fail_count: int, success_result: str = "success"):
    """Create async function that fails N times then succeeds."""
    call_count = [0]
    failing_func = _create_failing_func(call_count, fail_count, success_result)
    return failing_func, lambda: call_count[0]


def create_mock_database():
    """Create a mock database with standard methods."""
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


def _create_secret_manager_class():
    """Create MockSecretManager class."""
    from cryptography.fernet import Fernet
    class MockSecretManager:
        def __init__(self, key):
            self.fernet = Fernet(key)
            self.old_keys = []
    return MockSecretManager


def _create_logger_class():
    """Create MockUnifiedLogger class."""
    class MockUnifiedLogger:
        def __init__(self):
            self.correlation_id = None
            self.context = {}
            self.logs = []
    return MockUnifiedLogger


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


def create_mock_secret_manager_with_rotation():
    """Create secret manager that supports key rotation."""
    MockSecretManager = _create_secret_manager_class()
    _add_secret_manager_methods(MockSecretManager)
    return MockSecretManager


def _add_secret_manager_methods(cls):
    """Add methods to MockSecretManager class."""
    _add_secret_encryption_methods(cls)
    _add_secret_rotation_methods(cls)
    _add_secret_storage_methods(cls)
    _add_secret_decryption_methods(cls)


def _add_secret_encryption_methods(cls):
    """Add encryption methods to secret manager."""
    def encrypt_secret(self, secret: str) -> str:
        return self.fernet.encrypt(secret.encode()).decode()
    cls.encrypt_secret = encrypt_secret


def _add_secret_rotation_methods(cls):
    """Add key rotation methods to secret manager."""
    from cryptography.fernet import Fernet
    def rotate_key(self, new_key):
        self.old_keys.append(self.fernet)
        self.fernet = Fernet(new_key)
    cls.rotate_key = rotate_key


def _add_secret_storage_methods(cls):
    """Add storage methods to secret manager."""
    def store_secrets(self, secrets: Dict, path: str):
        pass  # Mock implementation
    def load_secrets(self, path: str) -> Dict:
        return {"api_key": "secret_key_123", "db_password": "password_456"}
    cls.store_secrets = store_secrets
    cls.load_secrets = load_secrets


def _add_secret_decryption_methods(cls):
    """Add decryption methods to secret manager."""
    def decrypt_secret(self, encrypted: str) -> str:
        return self._try_decrypt_with_current_and_old_keys(encrypted)
    def _try_decrypt_with_current_and_old_keys(self, encrypted: str) -> str:
        return _decrypt_with_keys(self, encrypted)
    cls.decrypt_secret = decrypt_secret
    cls._try_decrypt_with_current_and_old_keys = _try_decrypt_with_current_and_old_keys


def _decrypt_with_keys(manager, encrypted: str) -> str:
    """Try decryption with current and old keys."""
    try:
        return manager.fernet.decrypt(encrypted.encode()).decode()
    except:
        return _decrypt_with_old_keys(manager, encrypted)


def create_unified_logger_with_context():
    """Create unified logger with context management."""
    MockUnifiedLogger = _create_logger_class()
    _add_logger_methods(MockUnifiedLogger)
    return MockUnifiedLogger


def _decrypt_with_old_keys(manager, encrypted: str) -> str:
    """Try decryption with old keys."""
    for old_fernet in manager.old_keys:
        try:
            return old_fernet.decrypt(encrypted.encode()).decode()
        except:
            continue
    raise


def _add_logger_methods(cls):
    """Add methods to MockUnifiedLogger class."""
    _add_logger_context_methods(cls)
    _add_logger_logging_methods(cls)


def _add_logger_context_methods(cls):
    """Add context management methods to logger."""
    def set_correlation_id(self, correlation_id: str):
        self.correlation_id = correlation_id
    def add_context(self, context: Dict):
        self.context.update(context)
    cls.set_correlation_id = set_correlation_id
    cls.add_context = add_context


def _add_logger_logging_methods(cls):
    """Add logging methods to logger."""
    def log(self, level: str, message: str, **kwargs) -> Dict:
        log_entry = _create_log_entry(self, level, message, kwargs)
        self.logs.append(log_entry)
        return log_entry
    def get_aggregated_logs(self) -> List[Dict]:
        return self.logs
    cls.log = log
    cls.get_aggregated_logs = get_aggregated_logs


def _create_log_entry(logger, level: str, message: str, kwargs: Dict) -> Dict:
    """Create log entry with all context."""
    return {
        "level": level,
        "message": message,
        "correlation_id": logger.correlation_id,
        **logger.context,
        **kwargs
    }


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
    critical_up = all(service in ["database", "auth"] for service in critical_services)
    if critical_up:
        assert can_start  # Should start with critical services up