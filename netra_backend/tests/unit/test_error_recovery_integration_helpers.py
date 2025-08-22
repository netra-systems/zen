"""Utilities Tests - Split from test_error_recovery_integration.py"""

# Add project root to path
import sys
from pathlib import Path

from tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.core.agent_recovery_types import AgentType
from app.core.error_codes import ErrorSeverity

# Add project root to path
from app.core.error_recovery import OperationType

# Add project root to path


class ErrorRecoveryTestHelper:
    """Helper class for error recovery testing."""
    
    def get_breaker_side_effect(self, name):
        """Get circuit breaker side effect for testing."""
        if name.startswith('db_'):
            return Mock(name=f"db_breaker_{name}")
        elif name.startswith('api_'):
            return Mock(name=f"api_breaker_{name}")
        return Mock()
