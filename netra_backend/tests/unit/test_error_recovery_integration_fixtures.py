"""Fixtures Tests - Split from test_error_recovery_integration.py"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from app.core.error_recovery import OperationType
from app.core.error_codes import ErrorSeverity
from app.core.agent_recovery_types import AgentType


class EnhancedErrorRecoverySystem:
    """Mock class for testing."""
    def __init__(self):
        self.active = True


@pytest.fixture
def mock_error():
    """Create mock error for testing."""
    return ConnectionError("Test connection error")


@pytest.fixture
def recovery_system():
    """Create recovery system instance for testing."""
    return EnhancedErrorRecoverySystem()
