"""Core Tests - Split from test_jwt_token_propagation.py

Business Value Justification (BVJ):
- Segment: ALL (Free, Early, Mid, Enterprise)
- Business Goal: Authentication Reliability
- Value Impact: Ensures seamless user session management across all services
- Revenue Impact: Protects $25K MRR from auth-related user dropoffs

Tests token generation in auth service, validation in backend,
usage in frontend WebSocket, and token refresh flows.
"""

import asyncio
import time
import pytest
import jwt
import json
from typing import Dict, Optional, Any
import httpx
import websockets
from datetime import datetime, timedelta
from app.core.secret_manager import SecretManager
from test_framework.real_service_helper import RealServiceHelper

    def __init__(self):
        self.auth_url = "http://localhost:8001"
        self.backend_url = "http://localhost:8000"
        self.frontend_url = "http://localhost:3000"
        self.ws_url = "ws://localhost:8000/ws"
        self.service_helper = RealServiceHelper()
        self.secret_manager = SecretManager()
        self.jwt_secret: Optional[str] = None
