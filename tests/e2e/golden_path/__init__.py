"""
Golden Path E2E Tests

This package contains the MISSION CRITICAL tests that validate the complete golden path
user journey from initial connection through AI-powered business value delivery.

CRITICAL BUSINESS CONTEXT:
These tests protect $500K+ ARR by ensuring the core revenue-generating user flow works:
User Opens Chat → Authentication → Cost Optimization Request → Agent Pipeline → Business Value

PRIMARY TEST:
- test_complete_golden_path_business_value.py: THE primary revenue protection test

All tests in this package:
1. Use REAL services (no mocks in E2E)
2. Use REAL authentication (JWT/OAuth) 
3. Use REAL WebSocket connections
4. Use REAL LLM agents
5. Validate REAL business value delivery
6. Follow SSOT patterns from test_framework/

FAILURE of these tests indicates fundamental revenue-threatening system breakdown.
"""

__all__ = [
    "TestCompleteGoldenPathBusinessValue"
]