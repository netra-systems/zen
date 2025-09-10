"""Graceful Degradation Handler - Service Startup Failure Management

Business Value Justification (BVJ):
- Segment: Platform/Internal - Service Infrastructure  
- Business Goal: Ensure reliable service startup and dependency management
- Value Impact: Prevents service failures that block user access and revenue
- Strategic Impact: Core infrastructure reliability for business operations

This module provides SSOT compatibility by aliasing the existing 
GracefulDegradationManager implementation to GracefulDegradationHandler
for test compatibility while maintaining architectural integrity.
"""

# SSOT Import: Use existing GracefulDegradationManager from error handling service
from netra_backend.app.services.error_handling.graceful_degradation import (
    GracefulDegradationManager as GracefulDegradationHandler,
    ServiceStatus,
    DegradationLevel,
    ServiceHealthStatus
)

# Export for test compatibility
__all__ = [
    'GracefulDegradationHandler',
    'ServiceStatus', 
    'DegradationLevel',
    'ServiceHealthStatus'
]