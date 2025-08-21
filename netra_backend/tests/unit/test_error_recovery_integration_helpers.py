"""Utilities Tests - Split from test_error_recovery_integration.py"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from netra_backend.app.core.error_recovery import OperationType
from netra_backend.app.core.error_codes import ErrorSeverity
from netra_backend.app.core.agent_recovery_types import AgentType

# Add project root to path
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()



class ErrorRecoveryTestHelper:
    """Helper class for error recovery testing."""
    
    def get_breaker_side_effect(self, name):
        """Get circuit breaker side effect for testing."""
        if name.startswith('db_'):
            return Mock(name=f"db_breaker_{name}")
        elif name.startswith('api_'):
            return Mock(name=f"api_breaker_{name}")
        return Mock()
