"""
Auth Service Test Configuration Module
Test configuration and environment management for auth service tests
"""

# Import only from available shared modules
from shared.isolated_environment import IsolatedEnvironment

# Create aliases for backward compatibility
AuthTestEnvironment = IsolatedEnvironment

def load_test_config():
    """Load test configuration"""
    return {}

__all__ = ["AuthTestEnvironment", "load_test_config"]
