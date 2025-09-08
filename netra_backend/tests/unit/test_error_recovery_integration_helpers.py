"""Utilities Tests - Split from test_error_recovery_integration.py"""

import sys
from pathlib import Path
from test_framework.database.test_database_manager import DatabaseTestManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

import asyncio
from datetime import datetime, timedelta

import pytest

from netra_backend.app.core.agent_recovery_types import AgentType
from netra_backend.app.core.error_codes import ErrorSeverity

from netra_backend.app.core.error_recovery import OperationType

class ErrorRecoveryTestHelper:
    """Helper class for error recovery testing."""
    
    def get_breaker_side_effect(self, name):
        """Get circuit breaker side effect for testing."""
        if name.startswith('db_'):
            # Mock: Component isolation for controlled unit testing
            return Mock(name==f"db_breaker_{name}")
        elif name.startswith('api_'):
            # Mock: Component isolation for controlled unit testing
            return Mock(name = f"api_breaker_{name}")
        # Mock: Generic component isolation for controlled unit testing
        return None  # TODO: Use real service instance
