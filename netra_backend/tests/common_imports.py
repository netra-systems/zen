"""
Netra Backend Common - Consolidated Imports
============================================================
Consolidated imports for performance optimization in test infrastructure

USAGE:
    from tests.common_imports import *

PERFORMANCE: This module consolidates commonly used imports to reduce
import overhead and improve test collection performance.
"""

# CONSOLIDATED IMPORTS FOR PERFORMANCE
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.core.agent_execution_tracker import AgentExecutionTracker
from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
from netra_backend.app.services.redis_client import get_redis_client
from netra_backend.app.db.clickhouse import get_clickhouse_client

# Export commonly used classes and functions
__all__ = [
    'SSotAsyncTestCase', 'SSotBaseTestCase', 'SSotMockFactory',
    'DatabaseTestUtilities', 'UnifiedDockerManager',
    'UserExecutionContext', 'AgentExecutionTracker',
    'get_websocket_manager', 'get_redis_client', 'get_clickhouse_client',
    'unittest', 'asyncio', 'pytest'
]
