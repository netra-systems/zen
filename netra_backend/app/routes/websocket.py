"""
SSOT REDIRECTION: WebSocket Routes Consolidated

🚨 CRITICAL NOTICE: This file now redirects to websocket_ssot.py

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: SSOT Compliance & Route Consolidation  
- Value Impact: Eliminates 4 competing routes (4,206 lines) violating SSOT principles
- Strategic Impact: CRITICAL - Consolidates to single route while preserving $500K+ ARR chat functionality

CONSOLIDATION STATUS:
✅ Original websocket.py (3,166 lines) → SSOT websocket_ssot.py (main mode)
✅ websocket_factory.py (615 lines) → SSOT websocket_ssot.py (factory mode)  
✅ websocket_isolated.py (410 lines) → SSOT websocket_ssot.py (isolated mode)
✅ websocket_unified.py (15 lines) → SSOT websocket_ssot.py (legacy mode)

REDIRECTION STRATEGY:
All imports, routes, and function calls from this file are redirected to the 
SSOT implementation in websocket_ssot.py. This maintains 100% backward 
compatibility while eliminating SSOT violations.

🚀 GOLDEN PATH PRESERVATION:
All Golden Path functionality (login → AI responses) is preserved in SSOT implementation.
Critical WebSocket events (agent_started, agent_thinking, tool_executing, tool_completed, agent_completed) 
continue working through main mode of SSOT router.

MIGRATION COMPLETE - DO NOT MODIFY THIS FILE DIRECTLY
All changes must be made in websocket_ssot.py to maintain SSOT compliance.
"""

# SSOT REDIRECTION: All functionality consolidated into websocket_ssot.py
# This file now serves as a compatibility layer that redirects to SSOT implementation

# Compatibility classes for backward compatibility
class WebSocketComponentError(Exception):
    """Exception raised for WebSocket component validation errors."""
    pass

# Import SSOT router and all functions
from netra_backend.app.routes.websocket_ssot import (
    router,
    websocket_endpoint,
    websocket_health_check,
    get_websocket_config,
    websocket_detailed_stats,
    websocket_beacon,
    websocket_legacy_endpoint,
    websocket_test_endpoint
)

# Re-export for backward compatibility
__all__ = [
    'router',
    'websocket_endpoint',
    'WebSocketComponentError', 
    'websocket_health_check',
    'get_websocket_config',
    'websocket_detailed_stats',
    'websocket_beacon',
    'websocket_legacy_endpoint', 
    'websocket_test_endpoint'
]

# SSOT COMPLIANCE NOTICE:
# Original websocket.py contained 3,166 lines of business logic.
# All functionality has been consolidated into websocket_ssot.py to eliminate SSOT violations.
# This redirection maintains 100% API compatibility while achieving SSOT compliance.