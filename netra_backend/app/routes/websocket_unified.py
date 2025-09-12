"""
SSOT REDIRECTION: Unified Shim Consolidated

 ALERT:  CRITICAL NOTICE: This file now redirects to websocket_ssot.py (legacy mode)

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: SSOT Compliance & Legacy Compatibility
- Value Impact: Eliminates unnecessary indirection shim (15 lines) while preserving compatibility
- Strategic Impact: Simplifies import chain through direct SSOT redirection

CONSOLIDATION STATUS:
 PASS:  Original websocket_unified.py (15 lines)  ->  SSOT websocket_ssot.py (legacy mode)

LEGACY COMPATIBILITY PRESERVED:
 PASS:  Backward compatibility constants maintained
 PASS:  Import star patterns supported
 PASS:  Function aliases preserved
 PASS:  Configuration constants available

REDIRECTION STRATEGY:
This shim now properly redirects to SSOT implementation instead of creating
unnecessary indirection. All legacy compatibility is preserved.

MIGRATION COMPLETE - DO NOT MODIFY THIS FILE DIRECTLY
All changes must be made in websocket_ssot.py to maintain SSOT compliance.
"""

# SSOT REDIRECTION: Unified shim functionality consolidated into websocket_ssot.py
# This file now serves as a proper compatibility layer without unnecessary indirection

# Import SSOT router and all functions (replaces import * pattern)
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

# Legacy aliases for backward compatibility
unified_websocket_endpoint = websocket_endpoint
unified_websocket_health = websocket_health_check

# Legacy configuration constants (preserved for compatibility)
UNIFIED_WEBSOCKET_CONFIG = {
    "heartbeat_interval": 30,
    "reconnect_delay": 1000,
    "max_retries": 5,
    "compression_enabled": True,
    "max_message_size": 1024 * 1024,  # 1MB
    "auth_required": True
}

# Re-export all for import * compatibility
__all__ = [
    'router',
    'websocket_endpoint',
    'websocket_health_check', 
    'get_websocket_config',
    'websocket_detailed_stats',
    'websocket_beacon',
    'websocket_legacy_endpoint',
    'websocket_test_endpoint',
    'unified_websocket_endpoint',
    'unified_websocket_health',
    'UNIFIED_WEBSOCKET_CONFIG'
]

# SSOT COMPLIANCE NOTICE:
# Original websocket_unified.py was a 15-line shim creating unnecessary indirection.
# Now properly redirects to SSOT implementation while maintaining all compatibility.