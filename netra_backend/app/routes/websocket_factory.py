"""
SSOT REDIRECTION: Factory Pattern WebSocket Routes Consolidated

 ALERT:  CRITICAL NOTICE: This file now redirects to websocket_ssot.py (factory mode)

Business Value Justification:
- Segment: Platform/Internal  
- Business Goal: SSOT Compliance & Factory Pattern Preservation
- Value Impact: Consolidates factory route (615 lines) into SSOT while preserving user isolation
- Strategic Impact: Critical - Maintains per-user isolation through SSOT factory mode

CONSOLIDATION STATUS:
 PASS:  Original websocket_factory.py (615 lines)  ->  SSOT websocket_ssot.py (factory mode)

FACTORY FEATURES PRESERVED IN SSOT:
 PASS:  Per-User WebSocket Emitters - Isolated event handling maintained
 PASS:  Factory Adapter Integration - Gradual migration support preserved  
 PASS:  Request-Scoped Context - Complete isolation between concurrent users
 PASS:  Health Monitoring - Per-user connection health tracking
 PASS:  Error Resilience - Graceful fallback patterns maintained

REDIRECTION STRATEGY:
All factory pattern functionality is preserved in websocket_ssot.py factory mode.
This maintains 100% factory pattern compatibility while eliminating SSOT violations.

MIGRATION COMPLETE - DO NOT MODIFY THIS FILE DIRECTLY
All changes must be made in websocket_ssot.py to maintain SSOT compliance.
"""

# SSOT REDIRECTION: Factory pattern functionality consolidated into websocket_ssot.py
# This file now serves as a compatibility layer that redirects to SSOT factory mode

# Import SSOT router and factory-specific functions
from netra_backend.app.routes.websocket_ssot import (
    router,
    websocket_factory_endpoint,
    ssot_router
)

# Factory mode endpoints for backward compatibility
websocket_endpoint = websocket_factory_endpoint

# Re-export for backward compatibility
__all__ = [
    'router',
    'websocket_endpoint',
    'websocket_factory_endpoint'
]

# SSOT COMPLIANCE NOTICE:
# Original websocket_factory.py contained 615 lines of factory pattern logic.
# All functionality has been consolidated into websocket_ssot.py factory mode to eliminate SSOT violations.
# Factory pattern isolation features are preserved through mode-based dispatching.