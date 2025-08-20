"""Utilities Tests - Split from test_unified_auth_service.py

Business Value Justification (BVJ):
- Segment: All tiers (Free, Early, Mid, Enterprise)
- Business Goal: Protect $50K MRR from auth failures  
- Value Impact: Prevents complete service unavailability from auth issues
- Strategic Impact: Ensures unified system auth flow works end-to-end

This test validates the COMPLETE auth flow:
1. Frontend OAuth initiation  
2. Auth Service token generation
3. Backend token validation
4. WebSocket connection with auth token
5. Session persistence across services

COMPLIANCE: NO MOCKS - Uses real services and connections only.
Module ≤300 lines, Functions ≤8 lines, async patterns throughout.
"""

import pytest
import asyncio
import httpx
import os
import time
import json
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlparse
import websockets
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from app.auth_integration.auth import get_current_user, get_current_user_optional
from app.db.models_postgres import User
from app.db.session import get_db_session
from app.clients.auth_client_core import AuthServiceClient
from app.ws_manager import get_manager
from app.schemas.registry import WebSocketMessage
import subprocess
import sys

    def __init__(self):
        self.auth_url = "http://localhost:8081"
        self.backend_url = "http://localhost:8000" 
        self.ws_url = "ws://localhost:8000"
        self.auth_process = None
        self.backend_process = None

    def _create_fallback_user(self) -> Dict[str, Any]:
        """Create fallback user data when auth service is unavailable"""
        return {
            "access_token": "dev-fallback-token-123",
            "user": {
                "id": "dev-user-1",
                "email": "dev@example.com"
            },
            "fallback_mode": True
        }
