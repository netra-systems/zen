"""Utilities Tests - Split from test_error_recovery_integration.py"""

import sys
from pathlib import Path

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, Mock, patch

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
            return Mock(name=f"db_breaker_{name}")
        elif name.startswith('api_'):
            # Mock: Component isolation for controlled unit testing
            return Mock(name=f"api_breaker_{name}")
        # Mock: Generic component isolation for controlled unit testing
        return Mock()
