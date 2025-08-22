"""
Auth Service Test Configuration Module
Test configuration and environment management for auth service tests
"""

from auth_service.tests.config.test_env import AuthTestEnvironment, load_test_config
from auth_service.tests.config.test_settings import MainTestSettings

__all__ = ["AuthTestEnvironment", "MainTestSettings", "load_test_config"]