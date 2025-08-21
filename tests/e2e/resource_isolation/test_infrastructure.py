"""
Resource Isolation Test Infrastructure

This module provides a simplified interface to the infrastructure components
for resource isolation testing.

The infrastructure has been split into focused modules to maintain file size limits:
- data_models.py - Data classes and configuration
- resource_monitor.py - Resource monitoring functionality  
- leak_detector.py - Resource leak detection
- performance_validator.py - Performance isolation validation
- quota_enforcer.py - Resource quota enforcement

Business Value Justification (BVJ):
- Segment: Enterprise (multi-tenant isolation requirements)
- Business Goal: Provide robust resource isolation testing infrastructure
- Value Impact: Ensures reliable operation of $500K+ enterprise contracts
- Revenue Impact: Essential for maintaining enterprise trust and SLA compliance
"""

# Re-export all infrastructure components for backward compatibility
from tests.e2e.resource_isolation.infrastructure import ResourceMetrics, TenantAgent, ResourceViolation, PerformanceImpactReport, RESOURCE_LIMITS, ResourceMonitor, ResourceLeakDetector, PerformanceIsolationValidator, QuotaEnforcer
    ResourceMetrics, TenantAgent, ResourceViolation, PerformanceImpactReport,
    RESOURCE_LIMITS, ResourceMonitor, ResourceLeakDetector, 
    PerformanceIsolationValidator, QuotaEnforcer
)

__all__ = [
    'ResourceMetrics', 'TenantAgent', 'ResourceViolation', 'PerformanceImpactReport',
    'RESOURCE_LIMITS', 'ResourceMonitor', 'ResourceLeakDetector', 
    'PerformanceIsolationValidator', 'QuotaEnforcer'
]
