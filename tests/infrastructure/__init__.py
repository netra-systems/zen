"""
Infrastructure Tests Module

Business Value Justification (BVJ):
- Segment: Platform/Internal - Infrastructure Integrity & Production Readiness  
- Business Goal: Validate critical infrastructure components work correctly
- Value Impact: Ensures production deployment stability and prevents service failures
- Strategic Impact: Foundation for reliable platform operations supporting $500K+ ARR

This module contains critical infrastructure validation tests that reproduce and validate
fixes for production environment issues that affect the Golden Path user experience.

Test Categories:
- GCP Load Balancer header forwarding validation
- Demo mode configuration and security testing  
- WebSocket 1011 error reproduction and recovery testing

All tests follow SSOT patterns and use real services (no mocks) per CLAUDE.md requirements.
"""

# Infrastructure test markers for pytest
INFRASTRUCTURE_TEST_MARKERS = [
    "infrastructure",
    "real_services", 
    "demo_mode",
    "websocket_errors",
    "security",
    "gcp_staging"
]

# Test timeout configurations (seconds)
INFRASTRUCTURE_TEST_TIMEOUTS = {
    "gcp_load_balancer": 60,
    "demo_mode_config": 30,
    "websocket_1011_reproduction": 60,
    "security_validation": 20,
    "connectivity_test": 45
}

# Infrastructure test environment requirements
REQUIRED_ENV_VARS = {
    "gcp_load_balancer_tests": [
        "GCP_STAGING_BACKEND_URL",
        "GCP_STAGING_WEBSOCKET_URL", 
        "INFRASTRUCTURE_TEST_AUTH_TOKEN"
    ],
    "demo_mode_tests": [
        "DEMO_MODE",
        "ENVIRONMENT",
        "DEMO_AUTO_USER",
        "DEMO_USER_EMAIL"
    ],
    "websocket_1011_tests": [
        "TEST_WEBSOCKET_URL",
        "TEST_BACKEND_URL"
    ]
}