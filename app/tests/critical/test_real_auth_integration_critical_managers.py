"""Managers Tests - Split from test_real_auth_integration_critical.py

Business Value Justification (BVJ):
- Segment: All paid tiers (Early, Mid, Enterprise)
- Business Goal: Protect customer authentication and prevent revenue loss
- Value Impact: Prevents authentication failures that cause 100% service unavailability
- Revenue Impact: Critical - Auth failures = immediate customer churn. Estimated -$50K+ MRR risk

This module replaces critical mocked auth tests with REAL service integration.
These tests are BUSINESS CRITICAL and must pass for production deployment.

ARCHITECTURE:
- NO MOCKS - Uses real auth service HTTP calls only
- Validates real database state changes
- Tests actual end-to-end authentication flows
- Ensures service availability and reliability

COMPLIANCE:
- Module ≤300 lines ✓
- Functions ≤8 lines ✓
- Strong typing with Pydantic ✓
"""

import pytest
import asyncio
import httpx
import os
import time
from typing import Dict, Any, Optional
from datetime import datetime
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.auth_integration.auth import (
from app.db.models_postgres import User
from app.db.session import get_db_session
from app.clients.auth_client_core import AuthServiceClient

    def __init__(self):
        self.auth_url = "http://localhost:8081"
        self.http_client = httpx.AsyncClient(timeout=30.0)
        self.auth_client = AuthServiceClient()
        self.test_users = []
