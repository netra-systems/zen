"""
Resource Monitor - SSOT Import Module

This module provides a single source of truth import for resource monitoring functionality.
It exports from the canonical ResourceMonitor implementation.

SSOT Compliance: Exports from the test_framework canonical resource monitor implementation.
"""

# SSOT Import - Export from the canonical resource monitor implementations
from test_framework.resource_monitor import DockerResourceMonitor, ResourceUsage, ResourceType

# Create ResourceMonitor alias for backward compatibility
ResourceMonitor = DockerResourceMonitor

# Export for backward compatibility
__all__ = ['ResourceMonitor', 'DockerResourceMonitor', 'ResourceUsage', 'ResourceType']