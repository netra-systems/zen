"""
Integration Test Base - SSOT Pattern for Integration Tests

This module provides the SSOT BaseIntegrationTest class for all integration tests
requiring real services and proper business value validation.

Business Value Justification (BVJ):
- Segment: Platform/Internal  
- Business Goal: Enable consistent, reliable integration testing patterns
- Value Impact: Ensures all integration tests follow SSOT patterns and use real services
- Strategic Impact: Maintains test quality and prevents mock-based test pollution
"""

# Import the actual BaseIntegrationTest from the correct location
from test_framework.base_integration_test import BaseIntegrationTest

# Re-export for SSOT compliance
__all__ = ["BaseIntegrationTest"]