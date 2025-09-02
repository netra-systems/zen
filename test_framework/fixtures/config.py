from shared.isolated_environment import get_env
"""
Configuration Test Fixtures

Provides fixtures for testing configuration and settings.
"""

import os
import tempfile
from typing import Dict, Any, Optional, List
from unittest.mock import Mock, patch
import json
import yaml
from pathlib import Path


class MockConfigLoader:
    """Mock configuration loader for testing."""
    
    def __init__(self):
        self.config_data = {}
        self.load_calls = []
        self.save_calls = []
        
    def load_config(self, source: str) -> Dict[str, Any]:
        """Load configuration from source."""
        self.load_calls.append(source)
        return self.config_data.get(source, {})
    
    def save_config(self, config: Dict[str, Any], target: str) -> bool:
        """Save configuration to target."""
        self.save_calls.append((target, config.copy()))
        self.config_data[target] = config.copy()
        return True
    
    def set_config_data(self, source: str, data: Dict[str, Any]):
        """Set configuration data for a source."""
        self.config_data[source] = data.copy()
    
    def clear(self):
        """Clear all configuration data."""
        self.config_data.clear()
        self.load_calls.clear()
        self.save_calls.clear()


class TemporaryConfigFile:
    """Manages temporary configuration files for testing."""
    
    def __init__(self, config_data: Dict[str, Any], file_format: str = 'json'):
        self.config_data = config_data
        self.file_format = file_format.lower()
        self.temp_file = None
        self.file_path = None
    
    def __enter__(self):
        """Create temporary config file."""
        suffix = f'.{self.file_format}'
        self.temp_file = tempfile.NamedTemporaryFile(
            mode='w', suffix=suffix, delete=False
        )
        
        if self.file_format == 'json':
            json.dump(self.config_data, self.temp_file, indent=2)
        elif self.file_format in ['yaml', 'yml']:
            yaml.dump(self.config_data, self.temp_file, default_flow_style=False)
        else:
            # Plain text format
            for key, value in self.config_data.items():
                self.temp_file.write(f"{key}={value}\n")
        
        self.temp_file.close()
        self.file_path = self.temp_file.name
        return self.file_path
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up temporary file."""
        if self.file_path and os.path.exists(self.file_path):
            os.unlink(self.file_path)


class MockEnvironment:
    """Mock environment variables for testing."""
    
    def __init__(self, env_vars: Dict[str, str] = None):
        self.env_vars = env_vars or {}
        self.original_env = {}
        self.patches = []
    
    def __enter__(self):
        """Apply environment variables."""
        # Store original values
        for key in self.env_vars:
            self.original_env[key] = os.environ.get(key)
            os.environ[key] = self.env_vars[key]
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Restore original environment."""
        for key, original_value in self.original_env.items():
            if original_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = original_value
    
    def set_var(self, key: str, value: str):
        """Set additional environment variable."""
        self.original_env[key] = os.environ.get(key)
        os.environ[key] = value


# Test configuration data

TEST_CONFIG_BASIC = {
    "app_name": "test_app",
    "version": "1.0.0",
    "environment": "test",
    "debug": True,
    "database": {
        "url": "sqlite:///test.db",
        "pool_size": 5,
        "timeout": 30
    },
    "redis": {
        "url": "redis://localhost:6379/0",
        "max_connections": 10
    },
    "logging": {
        "level": "DEBUG",
        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    }
}

TEST_CONFIG_MINIMAL = {
    "app_name": "minimal_test",
    "environment": "test"
}

TEST_CONFIG_COMPLEX = {
    "app_name": "complex_test",
    "version": "2.1.0",
    "environment": "production",
    "debug": False,
    "features": {
        "auth": {
            "enabled": True,
            "providers": ["oauth", "jwt", "basic"],
            "session_timeout": 3600,
            "max_attempts": 3
        },
        "caching": {
            "enabled": True,
            "backend": "redis",
            "ttl": 300,
            "key_prefix": "cache:"
        },
        "monitoring": {
            "enabled": True,
            "metrics": ["response_time", "error_rate", "throughput"],
            "alerts": {
                "email": ["admin@example.com"],
                "slack": "#alerts"
            }
        }
    },
    "database": {
        "url": "postgresql://user:pass@localhost:5432/mydb",
        "pool_size": 20,
        "timeout": 60,
        "retry_attempts": 3,
        "migrations": {
            "auto_run": False,
            "directory": "migrations/"
        }
    },
    "external_services": {
        "payment_gateway": {
            "url": "https://api.payment.com",
            "api_key": "${PAYMENT_API_KEY}",
            "timeout": 30,
            "retry_attempts": 3
        },
        "notification_service": {
            "url": "https://notifications.example.com",
            "token": "${NOTIFICATION_TOKEN}",
            "batch_size": 100
        }
    }
}

TEST_ENV_VARS = {
    "DATABASE_URL": "postgresql://testuser:testpass@localhost:5432/testdb",
    "REDIS_URL": "redis://localhost:6379/1",
    "SECRET_KEY": "test-secret-key-123",
    "API_KEY": "test-api-key-456",
    "ENVIRONMENT": "test",
    "DEBUG": "true",
    "LOG_LEVEL": "DEBUG",
    "PAYMENT_API_KEY": "test-payment-key",
    "NOTIFICATION_TOKEN": "test-notification-token"
}

TEST_CONFIG_WITH_SECRETS = {
    "database_url": "${DATABASE_URL}",
    "redis_url": "${REDIS_URL}",
    "secret_key": "${SECRET_KEY}",
    "api_key": "${API_KEY}",
    "payment": {
        "api_key": "${PAYMENT_API_KEY}"
    },
    "notifications": {
        "token": "${NOTIFICATION_TOKEN}"
    }
}


class ConfigValidator:
    """Configuration validator for testing."""
    
    def __init__(self):
        self.validation_errors = []
        self.required_fields = []
        self.field_types = {}
        self.custom_validators = {}
    
    def add_required_field(self, field_path: str, field_type: type = str):
        """Add required field validation."""
        self.required_fields.append(field_path)
        self.field_types[field_path] = field_type
    
    def add_custom_validator(self, field_path: str, validator_func):
        """Add custom validator function."""
        self.custom_validators[field_path] = validator_func
    
    def validate_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate configuration and return error messages."""
        self.validation_errors.clear()
        
        # Check required fields
        for field_path in self.required_fields:
            if not self._field_exists(config, field_path):
                self.validation_errors.append(f"Required field missing: {field_path}")
            else:
                # Check field type
                value = self._get_field_value(config, field_path)
                expected_type = self.field_types.get(field_path, str)
                if not isinstance(value, expected_type):
                    self.validation_errors.append(
                        f"Field {field_path} has wrong type. Expected {expected_type.__name__}, got {type(value).__name__}"
                    )
        
        # Run custom validators
        for field_path, validator_func in self.custom_validators.items():
            if self._field_exists(config, field_path):
                value = self._get_field_value(config, field_path)
                try:
                    error = validator_func(value)
                    if error:
                        self.validation_errors.append(f"Field {field_path}: {error}")
                except Exception as e:
                    self.validation_errors.append(f"Field {field_path} validation error: {str(e)}")
        
        return self.validation_errors.copy()
    
    def _field_exists(self, config: Dict[str, Any], field_path: str) -> bool:
        """Check if field exists in config."""
        keys = field_path.split('.')
        current = config
        
        for key in keys:
            if not isinstance(current, dict) or key not in current:
                return False
            current = current[key]
        
        return True
    
    def _get_field_value(self, config: Dict[str, Any], field_path: str):
        """Get field value from config."""
        keys = field_path.split('.')
        current = config
        
        for key in keys:
            current = current[key]
        
        return current


# Fixture functions

def create_temp_config(config_data: Dict[str, Any], file_format: str = 'json') -> TemporaryConfigFile:
    """Create temporary configuration file."""
    return TemporaryConfigFile(config_data, file_format)

def create_mock_env(env_vars: Dict[str, str] = None) -> MockEnvironment:
    """Create mock environment context."""
    return MockEnvironment(env_vars or TEST_ENV_VARS)

def create_config_loader() -> MockConfigLoader:
    """Create mock configuration loader."""
    return MockConfigLoader()

def create_config_validator() -> ConfigValidator:
    """Create configuration validator."""
    return ConfigValidator()

def setup_test_config(config_name: str = 'basic') -> Dict[str, Any]:
    """Set up test configuration data."""
    configs = {
        'basic': TEST_CONFIG_BASIC,
        'minimal': TEST_CONFIG_MINIMAL,
        'complex': TEST_CONFIG_COMPLEX,
        'with_secrets': TEST_CONFIG_WITH_SECRETS
    }
    
    return configs.get(config_name, TEST_CONFIG_BASIC).copy()

def validate_database_url(url: str) -> Optional[str]:
    """Validate database URL format."""
    if not url.startswith(('sqlite:', 'postgresql:', 'mysql:')):
        return "Invalid database URL scheme"
    return None

def validate_redis_url(url: str) -> Optional[str]:
    """Validate Redis URL format."""
    if not url.startswith('redis://'):
        return "Invalid Redis URL scheme"
    return None

def validate_positive_integer(value: int) -> Optional[str]:
    """Validate positive integer."""
    if not isinstance(value, int) or value <= 0:
        return "Value must be a positive integer"
    return None

def validate_email_list(emails: List[str]) -> Optional[str]:
    """Validate list of email addresses."""
    if not isinstance(emails, list):
        return "Must be a list of email addresses"
    
    for email in emails:
        if '@' not in email or '.' not in email:
            return f"Invalid email address: {email}"
    
    return None


# Common test configurations

DEFAULT_TEST_CONFIG = TEST_CONFIG_BASIC
PRODUCTION_TEST_CONFIG = TEST_CONFIG_COMPLEX
MINIMAL_TEST_CONFIG = TEST_CONFIG_MINIMAL

# Commonly used validators
COMMON_VALIDATORS = {
    'database.url': validate_database_url,
    'redis.url': validate_redis_url,
    'database.pool_size': validate_positive_integer,
    'database.timeout': validate_positive_integer
}
