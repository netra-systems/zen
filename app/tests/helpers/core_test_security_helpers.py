"""
Helper functions for core infrastructure security and logging tests.
Provides reusable security mock creation and logging utilities.
Split from core_test_helpers.py to maintain 450-line limit.
"""

from typing import Dict, Any, List
from cryptography.fernet import Fernet


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
    base_fields = _create_base_log_fields(level, message, logger.correlation_id)
    return {**base_fields, **logger.context, **kwargs}


def _create_base_log_fields(level: str, message: str, correlation_id: str) -> Dict:
    """Create base log entry fields."""
    return {"level": level, "message": message, "correlation_id": correlation_id}


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