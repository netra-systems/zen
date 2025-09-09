"""
Service Initializer - SSOT Import Alias for Existing Implementation

This module provides SSOT import compatibility by aliasing the existing
UnifiedServiceInitializer implementation from the unified service initializer module.

Business Value Justification (BVJ):
- Segment: Enterprise ($500K+ ARR) and Standard customers
- Business Goal: Ensure reliable service initialization and dependency management
- Value Impact: Prevents service startup failures and ensures proper system initialization
- Strategic Impact: Critical for system reliability and deployment consistency
"""

# SSOT Import: Use existing UnifiedServiceInitializer from unified service initializer module
from netra_backend.app.services.service_initialization.unified_service_initializer import (
    UnifiedServiceInitializer as ServiceInitializer,
    ServiceStatus,
    CRITICAL_SERVICES,
    DEGRADED_MODE_SERVICES
)

# Export for test compatibility
__all__ = [
    'ServiceInitializer',
    'ServiceStatus',
    'CRITICAL_SERVICES',
    'DEGRADED_MODE_SERVICES'
]