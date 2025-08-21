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

# Add project root to path
import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
import time
from datetime import datetime
from typing import Any, Dict, Optional

import httpx
import pytest
from clients.auth_client_core import AuthServiceClient
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Add project root to path
from netra_backend.app.db.models_postgres import User
from netra_backend.app.db.session import get_db_session

# Add project root to path


class RealUserSessionHelper:
    """Helper class for real user session management testing."""
    
    def __init__(self):
        self.auth_url = "http://localhost:8081"
        self.client = httpx.AsyncClient(timeout=15.0)
        self.created_users = []
        self.active_sessions = []
