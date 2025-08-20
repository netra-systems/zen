"""Utilities Tests - Split from test_auth_backend_integration.py

Business Value Justification (BVJ):
Segment: Enterprise (Critical security infrastructure for all tiers)
Business Goal: Zero authentication failures across service boundaries 
Value Impact: Enables secure multi-service architecture for Enterprise customers
Revenue Impact: $50K+ MRR per enterprise client requiring security compliance

Tests JWT token flow between Auth service (port 8001) and Backend (port 8000):
- Token generation in Auth service
- Token validation in Backend service  
- User data synchronization between services
- Session management consistency
- Cross-service authentication failures

CRITICAL: Uses REAL services with actual HTTP calls - NO MOCKS
"""

import pytest
import httpx
import jwt
import asyncio
from typing import Dict, Optional
from dataclasses import dataclass
from .test_harness import UnifiedTestHarness
from .real_http_client import RealHttpClient
import time

    def __init__(self, context: AuthBackendTestContext):
        self.context = context
        self.http_client = RealHttpClient()

    def _check_user_data_consistency(self, auth_user: Optional[Dict], 
                                   backend_user: Optional[Dict]) -> bool:
        """Check if user data is consistent between services."""
        if not auth_user or not backend_user:
            return False
        
        # Check key fields match
        auth_email = auth_user.get("email", "").lower()
        backend_email = backend_user.get("email", "").lower()
        
        return auth_email == backend_email
