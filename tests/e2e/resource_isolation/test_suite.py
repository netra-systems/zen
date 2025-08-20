"""
Resource Isolation Test Suite

This module provides a simplified interface to the test suite components
for resource isolation testing.

The test suite has been split into focused modules to maintain file size limits:
- test_suite_core.py - Core test suite implementation
- agent_manager.py - Tenant agent management
- workload_generator.py - Workload generation patterns
- fixtures.py - Pytest fixtures

Business Value Justification (BVJ):
- Segment: Enterprise (multi-tenant isolation requirements)
- Business Goal: Provide comprehensive resource isolation testing
- Value Impact: Ensures reliable operation of $500K+ enterprise contracts
- Revenue Impact: Essential for maintaining enterprise trust and SLA compliance
"""

# Re-export all suite components for backward compatibility
from .suite import (
    ResourceIsolationTestSuite, TEST_CONFIG, TenantAgentManager,
    WorkloadGenerator, resource_isolation_suite, tenant_agents
)

__all__ = [
    'ResourceIsolationTestSuite', 'TEST_CONFIG', 'TenantAgentManager',
    'WorkloadGenerator', 'resource_isolation_suite', 'tenant_agents'
]