"""
Service Abstraction Layer for Integration Tests

This module provides service abstractions that enable integration tests to run
with or without external service dependencies, following CLAUDE.MD requirements
for proper integration vs E2E test separation.
"""

from .integration_service_abstraction import (
    ServiceAvailability,
    ServiceStatus,
    IntegrationServiceAbstraction,
    IntegrationDatabaseService,
    IntegrationWebSocketService,
    IntegrationServiceManager
)

__all__ = [
    "ServiceAvailability",
    "ServiceStatus",
    "IntegrationServiceAbstraction", 
    "IntegrationDatabaseService",
    "IntegrationWebSocketService",
    "IntegrationServiceManager"
]