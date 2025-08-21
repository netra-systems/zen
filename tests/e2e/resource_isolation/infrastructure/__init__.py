"""
Resource Isolation Infrastructure Module

This module contains the core infrastructure for resource isolation testing,
split from the original test_infrastructure.py to maintain file size limits.
"""

from tests.e2e.resource_isolation.infrastructure.data_models import (
    ResourceMetrics, TenantAgent, ResourceViolation, PerformanceImpactReport, RESOURCE_LIMITS
)
from tests.e2e.resource_isolation.infrastructure.resource_monitor import ResourceMonitor
from tests.e2e.resource_isolation.infrastructure.leak_detector import ResourceLeakDetector
from tests.e2e.resource_isolation.infrastructure.performance_validator import PerformanceIsolationValidator
from tests.e2e.resource_isolation.infrastructure.quota_enforcer import QuotaEnforcer

__all__ = [
    'ResourceMetrics', 'TenantAgent', 'ResourceViolation', 'PerformanceImpactReport', 
    'RESOURCE_LIMITS', 'ResourceMonitor', 'ResourceLeakDetector', 
    'PerformanceIsolationValidator', 'QuotaEnforcer'
]
