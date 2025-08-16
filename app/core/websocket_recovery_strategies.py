"""WebSocket connection recovery and state restoration strategies.

Provides automatic reconnection, state synchronization, and graceful handling
of WebSocket connection failures with minimal user disruption.

This module aggregates WebSocket recovery components that have been split
into focused modules for better maintainability and compliance.
"""

from .websocket_recovery_types import (
    ConnectionState,
    ReconnectionReason,
    ConnectionMetrics,
    MessageState,
    ReconnectionConfig
)
from .websocket_connection_manager import WebSocketConnectionManager
from .websocket_recovery_manager import WebSocketRecoveryManager, websocket_recovery_manager

__all__ = [
    'ConnectionState',
    'ReconnectionReason', 
    'ConnectionMetrics',
    'MessageState',
    'ReconnectionConfig',
    'WebSocketConnectionManager',
    'WebSocketRecoveryManager',
    'websocket_recovery_manager'
]