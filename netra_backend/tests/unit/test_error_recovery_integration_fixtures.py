"""Fixtures Tests - Split from test_error_recovery_integration.py"""

from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

# Add project root to path

from netra_backend.app.core.error_recovery import OperationType
from netra_backend.app.core.error_codes import ErrorSeverity
from netra_backend.app.core.agent_recovery_types import AgentType

# Add project root to path


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
