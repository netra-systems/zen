"""Agent Tests - Split from test_error_recovery_integration.py"""

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

    def test_get_agent_type_enum(self, recovery_system):
        """Test agent type enum conversion."""
        from app.core.agent_recovery_types import AgentType
        
        assert recovery_system._get_agent_type_enum('triage') == AgentType.TRIAGE
        assert recovery_system._get_agent_type_enum('data_analysis') == AgentType.DATA_ANALYSIS
        assert recovery_system._get_agent_type_enum('unknown') is None
