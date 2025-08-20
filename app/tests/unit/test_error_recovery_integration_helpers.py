"""Utilities Tests - Split from test_error_recovery_integration.py"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from app.core.error_recovery_integration import (
from app.core.error_recovery import OperationType
from app.core.error_codes import ErrorSeverity
from app.core.agent_recovery_types import AgentType

        def get_breaker_side_effect(name):
            if name.startswith('db_'):
                return db_breaker
            elif name.startswith('api_'):
                return api_breaker
            return Mock()
