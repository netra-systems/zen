"""Utilities Tests - Split from test_redis_session_integration.py

BVJ: $15K MRR - Session management critical for user experience
Components: Redis → Session Manager → Backend Services
Critical: Users must maintain session state across service interactions
"""

import pytest
import asyncio
import json
import time
from typing import Dict, Any, Optional
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime, timedelta, timezone
from app.redis_manager import RedisManager
from app.schemas import UserInDB
from test_framework.mock_utils import mock_justified

    def _validate_session_structure(self, session: Dict[str, Any]) -> bool:
        """Validate session has required structure."""
        required_fields = ["user_id", "session_id", "created_at"]
        return all(field in session for field in required_fields)
