"""Fixtures Tests - Split from test_error_recovery_integration.py"""

import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest

from netra_backend.app.core.agent_recovery_types import AgentType
from netra_backend.app.core.error_codes import ErrorSeverity

from netra_backend.app.core.error_recovery import OperationType

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
