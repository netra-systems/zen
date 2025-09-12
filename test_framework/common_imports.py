"""
Test Framework Common - Consolidated Imports
============================================================
Consolidated imports for performance optimization in test infrastructure

USAGE:
    from test_framework.common_imports import *

PERFORMANCE: This module consolidates commonly used imports to reduce
import overhead and improve test collection performance.
"""

# CONSOLIDATED IMPORTS FOR PERFORMANCE
from test_framework.ssot.base_test_case import SSotAsyncTestCase, SSotBaseTestCase
from test_framework.ssot.mock_factory import SSotMockFactory
from test_framework.database_test_utilities import DatabaseTestUtilities
from test_framework.unified_docker_manager import UnifiedDockerManager
import unittest
import asyncio
import pytest

# Export commonly used classes and functions
__all__ = [
    'SSotAsyncTestCase', 'SSotBaseTestCase', 'SSotMockFactory',
    'DatabaseTestUtilities', 'UnifiedDockerManager',
    'UserExecutionContext', 'AgentExecutionTracker',
    'get_websocket_manager', 'get_redis_client', 'get_clickhouse_client',
    'unittest', 'asyncio', 'pytest'
]
