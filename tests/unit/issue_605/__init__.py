"""
Issue #605 Test Package - GCP Cold Start WebSocket E2E Test Infrastructure

This package contains unit tests for Issue #605 that validate WebSocket E2E test 
infrastructure issues during GCP cold start scenarios.

Test Modules:
- test_websocket_api_compatibility.py: WebSocket API compatibility issues
- test_staging_test_base_inheritance.py: Test base class inheritance issues  
- test_gcp_header_validation.py: GCP Load Balancer header handling issues

Business Value Justification (BVJ):
- Segment: Platform (ALL tiers depend on WebSocket infrastructure)
- Business Goal: Ensure WebSocket E2E test infrastructure reliability  
- Value Impact: Critical for $500K+ ARR Golden Path user flow validation
- Revenue Impact: Prevents WebSocket infrastructure failures that block chat functionality

FAILING TESTS FIRST Strategy: 
Tests in this package are designed to FAIL initially to prove issues exist.
After fixes are implemented, tests should PASS to validate resolution.
"""

__version__ = "1.0.0"
__author__ = "Netra Platform Team"