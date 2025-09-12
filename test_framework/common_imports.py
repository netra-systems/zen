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

# SSOT imports based on verified paths from SSOT_IMPORT_REGISTRY.md
# User Execution Context (CRITICAL SECURITY - VERIFIED 2025-09-11)
from netra_backend.app.services.user_execution_context import UserExecutionContext, UserContextManager

# Agent Execution Tracker (SSOT - VERIFIED 2025-09-11)
from netra_backend.app.core.agent_execution_tracker import AgentExecutionTracker, get_execution_tracker

# WebSocket Manager (CRITICAL - VERIFIED 2025-09-11)
from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager, WebSocketManager

# Redis Client (CRITICAL - VERIFIED 2025-09-11)
from netra_backend.app.services.redis_client import get_redis_client, get_redis_service

# ClickHouse Client (SSOT - VERIFIED 2025-09-11)
from netra_backend.app.db.clickhouse import ClickHouseService, ClickHouseClient, get_clickhouse_client

# Base Integration Test Classes (CRITICAL FOR GOLDEN PATH TESTS)
from test_framework.base_integration_test import (
    BaseIntegrationTest, DatabaseIntegrationTest, CacheIntegrationTest,
    WebSocketIntegrationTest, ServiceOrchestrationIntegrationTest
)

# Export commonly used classes and functions
__all__ = [
    'SSotAsyncTestCase', 'SSotBaseTestCase', 'SSotMockFactory',
    'DatabaseTestUtilities', 'UnifiedDockerManager',
    'UserExecutionContext', 'UserContextManager', 'AgentExecutionTracker', 'get_execution_tracker',
    'get_websocket_manager', 'WebSocketManager',
    'get_redis_client', 'get_redis_service',
    'get_clickhouse_client', 'ClickHouseService', 'ClickHouseClient',
    'BaseIntegrationTest', 'DatabaseIntegrationTest', 'CacheIntegrationTest',
    'WebSocketIntegrationTest', 'ServiceOrchestrationIntegrationTest',
    'unittest', 'asyncio', 'pytest'
]
