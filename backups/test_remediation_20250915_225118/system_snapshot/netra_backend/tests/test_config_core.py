# Shim module for config test helpers
# Import basic fixtures since config specific ones don't exist
from test_framework.fixtures import *
from shared.isolated_environment import IsolatedEnvironment

# Basic config test data
TEST_CONFIG_DATA = {
    "database_url": "postgresql://localhost:5433/netra_test",
    "redis_url": "redis://localhost:6379/0",
    "secret_key": "test_secret_key",
    "debug": True,
    "environment": "test"
}

def create_test_config(**overrides):
    """Create test configuration with optional overrides."""
    config = TEST_CONFIG_DATA.copy()
    config.update(overrides)
    return config

class ConfigStatusHelper:
    """Helper class for testing configuration status."""
    
    def __init__(self, valid: bool = True, errors: list = None):
        self.valid = valid
        self.errors = errors or []
    
    def is_valid(self) -> bool:
        return self.valid
    
    def get_errors(self) -> list:
        return self.errors
    
    def add_error(self, error: str):
        self.errors.append(error)
        self.valid = False


class ConfigValidationResultHelper:
    """Helper class for config validation results."""
    
    def __init__(self, valid: bool = True, message: str = "", details: dict = None):
        self.valid = valid
        self.message = message
        self.details = details or {}
        self.errors = []
    
    def is_valid(self) -> bool:
        return self.valid
    
    def get_message(self) -> str:
        return self.message
    
    def get_details(self) -> dict:
        return self.details
        
    def add_error(self, error: str):
        self.errors.append(error)
        self.valid = False


class ValidationContextHelper:
    """Helper class for testing validation context."""
    
    def __init__(self, config_path: str = "", is_interactive: bool = True, 
                 is_ci_environment: bool = False, cli_overrides: dict = None, 
                 env_overrides: dict = None):
        self.config_path = config_path
        self.is_interactive = is_interactive
        self.is_ci_environment = is_ci_environment
        self.cli_overrides = cli_overrides or {}
        self.env_overrides = env_overrides or {}
