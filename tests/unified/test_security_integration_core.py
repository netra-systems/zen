"""Core Tests - Split from test_security_integration.py

Business Value Justification (BVJ):
- Segment: Enterprise (security requirements are deal breakers)
- Business Goal: Enable Enterprise trust through comprehensive security validation
- Value Impact: Security compliance unlocks Enterprise deals worth $50K+ ARR each
- Revenue Impact: Each Enterprise customer represents 20x value of Mid-tier customers

Architecture:
- 450-line file limit enforced through modular test design
- 25-line function limit for all test methods
- Real service integration with zero mocking of security layers
- Covers OWASP Top 10 attack vectors with automated detection
"""

import pytest
import asyncio
import aiohttp
import json
from typing import Dict, Any, List
from unittest.mock import AsyncMock
from tests.unified.config import TEST_CONFIG, TEST_ENDPOINTS, get_test_user

    def create_malicious_headers() -> Dict[str, str]:
        """Create headers with malicious content"""
        return {
            "X-Forwarded-For": "<script>alert('xss')</script>",
            "User-Agent": "'; DROP TABLE sessions; --",
            "Referer": "javascript:alert('csrf')",
            "Origin": "http://evil-site.com"
        }

    def create_dos_requests(count: int = 100) -> List[Dict[str, Any]]:
        """Create high-volume requests for DoS testing"""
        requests = []
        for i in range(count):
            requests.append({"id": i, "payload": f"dos_test_{i}"})
        return requests

    def _assert_headers_present(response: aiohttp.ClientResponse, headers: List[str]) -> None:
        """Assert security headers are present in response"""
        for header in headers:
            assert header in response.headers, f"Missing security header: {header}"
