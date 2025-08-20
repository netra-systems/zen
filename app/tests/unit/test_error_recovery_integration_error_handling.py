"""Error_Handling Tests - Split from test_error_recovery_integration.py"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from app.core.error_recovery_integration import (
from app.core.error_recovery import OperationType
from app.core.error_codes import ErrorSeverity
from app.core.agent_recovery_types import AgentType

    def recovery_system(self):
        """Create recovery system instance for testing."""
        return EnhancedErrorRecoverySystem()

    def test_prepare_error_data(self, recovery_system):
        """Test error data preparation."""
        error = ValueError("Test error")
        
        result = recovery_system._prepare_error_data(
            'triage', 'classify', error, {'key': 'value'}, 'user123'
        )
        
        assert result['error_type'] == 'ValueError'
        assert result['module'] == 'agent_triage'
        assert result['function'] == 'classify'
        assert result['message'] == 'Test error'
        assert result['user_id'] == 'user123'
        assert result['context'] == {'key': 'value'}
        assert isinstance(result['timestamp'], datetime)
