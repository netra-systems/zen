"""Fixtures Tests - Split from test_error_recovery_integration.py"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from app.core.error_recovery_integration import (
from app.core.error_recovery import OperationType
from app.core.error_codes import ErrorSeverity
from app.core.agent_recovery_types import AgentType

def mock_error():
    """Create mock error for testing."""
    return ConnectionError("Test connection error")

    def recovery_system(self):
        """Create recovery system instance for testing."""
        return EnhancedErrorRecoverySystem()

    def mock_error(self):
        """Create mock error for testing."""
        return ConnectionError("Test connection error")
