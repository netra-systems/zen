from datetime import datetime
"""Utilities Tests - Split from test_logging_audit_integration.py"""

import sys
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

# Test framework import - using pytest fixtures instead

import asyncio
import json
import os
import tempfile
from datetime import UTC, datetime
from typing import Any, Dict, List

import pytest
from netra_backend.app.logging_config import central_logger, get_central_logger

from netra_backend.app.core.logging_context import (
    request_id_context,
    trace_id_context,
    user_id_context,
)
# Removed mock import - using real service testing per CLAUDE.md "MOCKS = Abomination"
from test_framework.real_services import get_real_services

class AuditEventHelper:
    """Helper class for audit events (renamed from TestSyntaxFix to avoid pytest collection)"""

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
            "request_id": self.request_id,
}
