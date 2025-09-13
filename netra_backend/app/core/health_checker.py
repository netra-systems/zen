"""
Health Checker Module - Compatibility Layer for Integration Tests

This module provides a compatibility layer for integration tests that expect
a health checker implementation. It re-exports from health_monitor.

CRITICAL ARCHITECTURAL COMPLIANCE:
- This is a COMPATIBILITY LAYER for integration tests
- Re-exports from health_monitor.py (SSOT)
- DO NOT add new functionality here

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Test Infrastructure Stability
- Value Impact: Enables integration test collection and execution
- Strategic Impact: Maintains test coverage during system evolution
"""

# Re-export everything from health_monitor
from netra_backend.app.core.health_monitor import *

# Create compatibility aliases
HealthChecker = HealthMonitor
health_checker = health_monitor

__all__ = [
    "HealthChecker",
    "health_checker",
    # Also export everything from health_monitor
    "HealthMonitor",
    "HealthCheck",
    "HealthCheckResult",
    "HealthStatus",
    "health_monitor"
]