"""
Shared type definitions (minimal vendored subset for zen --apex CLI).

This package provides WebSocket closure code utilities required by agent_cli.py.
"""

from shared.types.websocket_closure_codes import (
    WebSocketClosureCode,
    WebSocketClosureCategory,
    categorize_closure_code,
    get_closure_description,
    is_infrastructure_error
)

__all__ = [
    'WebSocketClosureCode',
    'WebSocketClosureCategory',
    'categorize_closure_code',
    'get_closure_description',
    'is_infrastructure_error'
]
