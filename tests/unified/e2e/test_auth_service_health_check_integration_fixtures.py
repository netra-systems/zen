"""Fixtures Tests - Split from test_auth_service_health_check_integration.py

Business Value Justification (BVJ):
- Segment: ALL (Free, Early, Mid, Enterprise, Platform/Internal)
- Business Goal: Service Reliability & Operational Stability
- Value Impact: Prevents auth service startup failures affecting $50K+ MRR
- Revenue Impact: Ensures authentication availability for all revenue streams
- Strategic Impact: Validates health check reliability for critical auth infrastructure

CRITICAL REQUIREMENTS:
1. Test Auth service health check endpoints with database initialization
2. Validate /health/ready endpoint responds correctly on port 8080 (not 8001)
3. Test that database connections initialize lazily if not already initialized
4. Ensure health checks handle uninitialized async_engine gracefully
5. Test service recovery from database failures
6. Performance requirement: <1s health check response

This test validates the Auth service health check system's reliability,
preventing service startup failures that could impact all customer segments.
Maximum 300 lines, async/await pattern, comprehensive scenarios.
"""

import asyncio
import time
import pytest
import httpx
import logging
import os
from typing import Dict, Any, Optional, List
from pathlib import Path
from dataclasses import dataclass
from unittest.mock import patch, AsyncMock
import sys
import asyncio

    def health_validator(self):
        """Create health validator instance."""
        return AuthServiceHealthValidator()

    def recovery_tester(self):
        """Create recovery tester instance."""
        return AuthServiceRecoveryTester()
