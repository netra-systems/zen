"""
SSOT REDIRECTION: Isolated WebSocket Routes Consolidated

🚨 CRITICAL NOTICE: This file now redirects to websocket_ssot.py (isolated mode)

Business Value Justification:
- Segment: All (Free → Enterprise)
- Business Goal: SSOT Compliance & Isolation Security Preservation
- Value Impact: Consolidates isolated route (410 lines) into SSOT while guaranteeing zero event leakage
- Strategic Impact: CRITICAL - Maintains secure multi-user chat through SSOT isolated mode

CONSOLIDATION STATUS:
✅ Original websocket_isolated.py (410 lines) → SSOT websocket_ssot.py (isolated mode)

ISOLATION FEATURES PRESERVED IN SSOT:
✅ Connection-scoped managers - No shared state between users
✅ User authentication validation on ALL connections  
✅ Event filtering - Only events for authenticated user delivered
✅ Automatic resource cleanup on disconnect
✅ Comprehensive audit logging for debugging

REDIRECTION STRATEGY:
All isolation functionality is preserved in websocket_ssot.py isolated mode.
This maintains 100% security guarantees while eliminating SSOT violations.

MIGRATION COMPLETE - DO NOT MODIFY THIS FILE DIRECTLY
All changes must be made in websocket_ssot.py to maintain SSOT compliance.
"""

# SSOT REDIRECTION: Isolated pattern functionality consolidated into websocket_ssot.py  
# This file now serves as a compatibility layer that redirects to SSOT isolated mode

# Import SSOT router and isolated-specific functions
from netra_backend.app.routes.websocket_ssot import (
    router,
    websocket_isolated_endpoint,
    ssot_router
)

# Isolated mode endpoints for backward compatibility  
websocket_endpoint = websocket_isolated_endpoint

# Re-export for backward compatibility
__all__ = [
    'router', 
    'websocket_endpoint',
    'websocket_isolated_endpoint'
]

# SSOT COMPLIANCE NOTICE:
# Original websocket_isolated.py contained 410 lines of isolation security logic.
# All functionality has been consolidated into websocket_ssot.py isolated mode to eliminate SSOT violations.
# Zero event leakage and connection-scoped isolation are preserved through mode-based dispatching.