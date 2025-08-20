"""Utilities Tests - Split from test_user_session_persistence_restart.py

Business Value Justification (BVJ):
- Segment: ALL (critical for user experience)
- Business Goal: User Retention & Experience
- Value Impact: Prevents user session loss during deployments/restarts
- Revenue Impact: Protects $18K MRR from session-related churn

Tests session creation, service restart handling, session validity
after restart, and data consistency across restarts.
"""

import asyncio
import time
import pytest
from typing import Dict, List, Optional, Any
import httpx
import redis.asyncio as redis
from datetime import datetime, timedelta
from test_framework.real_service_helper import RealServiceHelper
from app.services.session.session_manager import SessionManager
import websockets
import json
import json

    def __init__(self):
        self.auth_url = "http://localhost:8001"
        self.backend_url = "http://localhost:8000"
        self.ws_url = "ws://localhost:8000/ws"
        self.service_helper = RealServiceHelper()
        self.redis_client: Optional[redis.Redis] = None
        self.session_manager = SessionManager()
        self.active_sessions: List[Dict[str, Any]] = []
