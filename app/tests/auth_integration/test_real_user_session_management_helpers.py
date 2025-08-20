"""Utilities Tests - Split from test_real_user_session_management.py

Business Value Justification (BVJ):
- Segment: All paid tiers (Early, Mid, Enterprise)
- Business Goal: Protect user onboarding and session security
- Value Impact: Prevents user creation failures and session hijacking
- Revenue Impact: User creation issues = 100% customer churn. Session issues = security breaches

This module tests REAL user creation and session management with auth service.
Replaces mocked tests with actual service integration and database validation.

ARCHITECTURE:
- Tests real user creation via auth service endpoints
- Validates session creation, management, and destruction
- Ensures database state consistency for users and sessions
- NO MOCKING - Uses real HTTP calls and database queries

COMPLIANCE:
- Module ≤300 lines ✓
- Functions ≤8 lines ✓
- Strong typing with Pydantic ✓
"""

import pytest
import asyncio
import httpx
import time
from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException
from app.db.models_postgres import User
from app.db.session import get_db_session
from app.clients.auth_client_core import AuthServiceClient

    def __init__(self):
        self.auth_url = "http://localhost:8081"
        self.client = httpx.AsyncClient(timeout=15.0)
        self.created_users = []
        self.active_sessions = []
