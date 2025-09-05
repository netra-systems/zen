"""Test Framework Utilities Package

Provides utilities for integration testing with external services.
This is a critical component for L2/L3 realism testing.
"""

from .external_service_integration import (
    ExternalServiceIntegration,
    ServiceHealthChecker,
    TestDataGenerator
)

__all__ = [
    "ExternalServiceIntegration",
    "ServiceHealthChecker",
    "TestDataGenerator"
]