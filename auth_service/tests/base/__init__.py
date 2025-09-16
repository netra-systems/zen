"""
Auth Service Base Test Classes
Common test functionality and base classes for auth service testing
"""

# Import from SSOT test framework instead of non-existent local files
from test_framework.ssot.base_test_case import SSotBaseTestCase, SSotAsyncTestCase
from test_framework.base import BaseTestCase, AsyncTestCase

# Create auth-specific aliases for backward compatibility
AsyncTestBase = SSotAsyncTestCase
AuthTestBase = SSotBaseTestCase

__all__ = [
    "AuthTestBase",
    "AsyncTestBase",
    "BaseTestCase",
    "AsyncTestCase",
    "SSotBaseTestCase",
    "SSotAsyncTestCase"
]
