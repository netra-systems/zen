"""Utilities Tests - Split from test_real_auth_integration.py

Business Value Justification (BVJ):
- Segment: All paid tiers (Early, Mid, Enterprise) 
- Business Goal: Protect customer authentication and prevent revenue loss
- Value Impact: Prevents authentication failures that cause 100% service unavailability
- Revenue Impact: Critical - Auth failures = immediate customer churn. Estimated -$50K+ MRR risk

This module replaces mocked auth tests with REAL service integration tests.
Tests authenticate against the actual auth service and validate database state.

ARCHITECTURE:
- Starts real auth service on port 8081
- Makes real HTTP calls to auth endpoints  
- Validates real database state changes
- No mocking of internal auth components

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
from typing import Optional, Dict, Any
from datetime import datetime
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.auth_integration.auth import (
from app.db.models_postgres import User
from app.db.session import get_db_session
from app.clients.auth_client_core import AuthServiceClient
import subprocess
import sys

    def __init__(self):
        self.auth_process = None
        self.auth_url = "http://localhost:8081"
        self.client = httpx.AsyncClient()
