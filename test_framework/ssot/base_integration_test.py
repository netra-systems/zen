"""
Base Integration Test - SSOT Import Module

This module provides the SSOT import path for BaseIntegrationTest classes.
Ensures consistent import paths across the test framework infrastructure.

Business Value Justification (BVJ):
- Segment: Platform/Internal  
- Business Goal: Enable consistent SSOT import patterns for integration tests
- Value Impact: Prevents import errors and maintains test framework stability
- Strategic Impact: Ensures all integration tests use standardized base classes
"""

# Import the actual BaseIntegrationTest classes from the correct location
from test_framework.base_integration_test import (
    BaseIntegrationTest,
    DatabaseIntegrationTest,
    CacheIntegrationTest,
    WebSocketIntegrationTest,
    ServiceOrchestrationIntegrationTest
)

# Re-export all classes for SSOT compliance
__all__ = [
    "BaseIntegrationTest",
    "DatabaseIntegrationTest", 
    "CacheIntegrationTest",
    "WebSocketIntegrationTest",
    "ServiceOrchestrationIntegrationTest"
]