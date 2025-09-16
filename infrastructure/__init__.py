"""
Infrastructure utilities for VPC connectivity and system remediation.

SSOT COMPLIANCE: This module provides centralized infrastructure validation
for cross-platform deployment testing and remediation.

CRITICAL MISSION: Supports Golden Path testing by enabling proper infrastructure
validation imports across Windows and Unix platforms.

Usage:
    from infrastructure import VPCConnectivityValidator
    from infrastructure import check_vpc_connectivity
"""

from .vpc_connectivity_fix import (
    VPCConnectivityValidator,
    VPCConnectivityStatus,
    VPCConnectivityFixer,
    check_vpc_connectivity,
    get_vpc_connectivity_status
)

from .websocket_auth_remediation import (
    WebSocketAuthManager,
    WebSocketAuthResult,
    AuthServiceHealthStatus,
    WebSocketAuthenticationError,
    WebSocketAuthHelpers
)

__all__ = [
    'VPCConnectivityValidator',
    'VPCConnectivityStatus',
    'VPCConnectivityFixer',
    'check_vpc_connectivity',
    'get_vpc_connectivity_status',
    'WebSocketAuthManager',
    'WebSocketAuthResult',
    'AuthServiceHealthStatus',
    'WebSocketAuthenticationError',
    'WebSocketAuthHelpers'
]