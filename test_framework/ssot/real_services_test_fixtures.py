"""
SSOT Real Services Test Fixtures

This module provides the Single Source of Truth (SSOT) for real services
test fixtures used across integration and E2E testing.

Business Value:
- Segment: Platform/Internal - Test Infrastructure
- Business Goal: Development Velocity & Test Reliability
- Value Impact: Consistent real services testing across all test suites
- Strategic Impact: Foundation for reliable integration testing

This module imports and re-exports fixtures from the main real services
fixtures to maintain SSOT compliance while providing backward compatibility.
"""

# Import all fixtures from the canonical real services module
from test_framework.fixtures.real_services import (
    real_postgres_connection,
    with_test_database,
    real_redis_fixture,
    real_services_fixture
)

# Re-export for SSOT compliance
__all__ = [
    "real_postgres_connection",
    "with_test_database",
    "real_redis_fixture", 
    "real_services_fixture"
]