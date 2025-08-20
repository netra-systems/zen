"""Utilities Tests - Split from test_logging_audit_integration.py"""

import pytest
import asyncio
import json
import tempfile
import os
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List
from datetime import datetime, UTC
from app.logging_config import central_logger, get_central_logger
from app.core.logging_context import request_id_context, user_id_context, trace_id_context
from test_framework.mock_utils import mock_justified

    def __init__(self, event_type: str, user_id: str, resource: str, action: str):
        self.event_type = event_type
        self.user_id = user_id
        self.resource = resource
        self.action = action
        self.timestamp = datetime.now(UTC)
        self.request_id = "test_request_123"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            "event_type": self.event_type,
            "user_id": self.user_id,
            "resource": self.resource,
            "action": self.action,
            "timestamp": self.timestamp.isoformat(),
            "request_id": self.request_id
        }
