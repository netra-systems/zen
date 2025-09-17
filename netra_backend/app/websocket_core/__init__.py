"""
WebSocket Core - Unified SSOT Implementation

MISSION CRITICAL: Enables chat value delivery through 5 critical events.
Single source of truth for all WebSocket functionality.

Business Value:
- Consolidates 13+ files into 2 unified implementations
- Ensures 100% critical event delivery
- Zero cross-user event leakage
"""

# Unified implementations (SSOT)
# ISSUE #1144 SSOT CONSOLIDATION: Phase 1 - Deprecate __init__.py imports
# DEPRECATED: from netra_backend.app.websocket_core import WebSocketManager
# CANONICAL: from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
#
# MIGRATION PLAN:
# - Phase 1: Update key consumers to use canonical imports (IN PROGRESS)
# - Phase 2: Remove __init__.py exports entirely
# - Phase 3: Consolidate implementation layers
import warnings
import inspect

# ISSUE #1090 PHASE 3 FIX: Targeted deprecation warning system
def _check_direct_import_and_warn():
    """
    Check if this module is being imported directly and warn appropriately.
    
    ISSUE #1090 FIX: This targeted approach distinguishes between:
    1. Direct imports from websocket_core.__init__ (SHOULD warn)
    2. Specific module imports like event_validator.UnifiedEventValidator (should NOT warn)
    
    The key distinction is whether the import line contains the specific submodule path.
    """
    import traceback
    
    # Get the current call stack
    stack = traceback.extract_stack()
    
    # Look for the frame that contains the import statement
    for frame in reversed(stack):
        # Skip this file and internal Python machinery
        if frame.filename == __file__ or 'importlib' in frame.filename or '<frozen' in frame.filename:
            continue
            
        # Read the source line to check the import pattern
        try:
            with open(frame.filename, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                if frame.lineno <= len(lines):
                    line = lines[frame.lineno - 1].strip()
                    
                    # ISSUE #1090 FIX: Only warn for DIRECT imports from websocket_core 
                    # Do NOT warn for specific module imports
                    if 'from netra_backend.app.websocket_core import' in line:
                        # Check if this is a specific module import (should NOT warn)
                        # Example: from netra_backend.app.websocket_core.event_validator import UnifiedEventValidator
                        specific_module_patterns = [
                            'websocket_core.websocket_manager',
                            'websocket_core.event_validator',
                            'websocket_core.unified_emitter', 
                            'websocket_core.handlers',
                            'websocket_core.types',
                            'websocket_core.utils',
                            'websocket_core.auth',
                            'websocket_core.context',
                            'websocket_core.migration_adapter',
                            'websocket_core.user_context_extractor',
                            'websocket_core.protocols',
                            'websocket_core.race_condition_prevention',
                            'websocket_core.connection_state_machine',
                            'websocket_core.message_queue',
                            'websocket_core.canonical_import_patterns',
                            'websocket_core.unified_manager'
                        ]
                        
                        # If line contains a specific module path, do NOT warn
                        if any(pattern in line for pattern in specific_module_patterns):
                            return  # This is a legitimate specific import - no warning
                        
                        # This is a direct import from __init__.py - issue targeted warning
                        warnings.warn(
                            f"ISSUE #1144: Direct import from 'netra_backend.app.websocket_core' is deprecated. "
                            f"Use specific module imports like 'from netra_backend.app.websocket_core.websocket_manager import WebSocketManager'. "
                            f"This import path will be removed in Phase 2 of SSOT consolidation.",
                            DeprecationWarning,
                            stacklevel=2
                        )
                        return
        except (IOError, IndexError, OSError):
            # If we can't read the file, skip this frame
            continue
        
        # Only check the first non-internal frame
        break

# Call the warning check - now properly targeted for Issue #1090
_check_direct_import_and_warn()

# ISSUE #1176 PHASE 2 REMEDIATION: SSOT Canonical Import Consolidation
# COORDINATION FIX: Eliminate import path fragmentation by using single canonical strategy
# DECISION: Remove __init__.py exports to force consistent direct imports from specific modules

# DEPRECATION NOTICE: __init__.py imports are deprecated in favor of direct module imports
# Use: from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
# Use: from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
import warnings

def _emit_deprecation_warning():
    """Emit deprecation warning for __init__.py imports."""
    warnings.warn(
        "ISSUE #1176 Phase 2: Importing from websocket_core.__init__ is deprecated. "
        "Use direct imports from specific modules: "
        "from netra_backend.app.websocket_core.websocket_manager import WebSocketManager",
        DeprecationWarning,
        stacklevel=3
    )

# Only import for absolute necessity - prefer empty __init__.py for SSOT compliance
# _emit_deprecation_warning()

# ISSUE #1176 PHASE 2 REMEDIATION: MINIMAL imports to force canonical direct imports
# COORDINATION STRATEGY: Provide only absolutely critical imports needed for backward compatibility

# Minimal imports for critical backward compatibility only
try:
    from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
    from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
    from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
    from netra_backend.app.websocket_core.protocols import WebSocketManagerProtocol

    # REMEDIATION: Add missing exports for test compatibility (Issue #1176 Phase 2 Fix)
    from netra_backend.app.websocket_core.types import create_server_message, create_error_message

    # ISSUE #1286 FIX: Add missing get_websocket_manager export for test compatibility
    from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager

    # ISSUE #1286 FIX: Add missing create_test_user_context export for test compatibility
    from netra_backend.app.websocket_core.websocket_manager import create_test_user_context
except ImportError as e:
    # FAIL FAST: Critical WebSocket components must be available
    raise ImportError(
        f"CRITICAL: Core WebSocket components import failed: {e}. "
        f"This indicates a dependency issue that must be resolved."
    ) from e

# REMEDIATION: Optional imports for test compatibility (may not exist in all environments)
try:
    from netra_backend.app.websocket_core.connection_state_machine import ConnectionStateMachine
except ImportError:
    ConnectionStateMachine = None

try:
    from netra_backend.app.websocket_core.message_queue import MessageQueue
except ImportError:
    MessageQueue = None

try:
    from netra_backend.app.websocket_core.websocket_manager import websocket_manager
except ImportError:
    websocket_manager = None

# ISSUE #1176 PHASE 2 REMEDIATION: Add missing get_connection_monitor for test compatibility
try:
    from netra_backend.app.websocket_core.utils import get_connection_monitor
except ImportError:
    get_connection_monitor = None

# REMEDIATION: Add missing WebSocketHeartbeat export for test compatibility
try:
    from netra_backend.app.websocket_core.utils import WebSocketHeartbeat
except ImportError:
    WebSocketHeartbeat = None

# ISSUE #1176 PHASE 2 REMEDIATION: Add missing get_websocket_manager for test compatibility
try:
    from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
except ImportError:
    get_websocket_manager = None

# SSOT COMPLIANCE: Factory pattern eliminated - use direct WebSocketManager import
# from netra_backend.app.websocket_core.websocket_manager_factory import (
#     WebSocketManagerFactory,  # REMOVED: Issue #1098 - Use get_websocket_manager() instead
#     IsolatedWebSocketManager,
#     get_websocket_manager_factory,
#     create_websocket_manager
# )

# Backward compatibility function for create_websocket_manager
def create_websocket_manager(user_context=None):
    """
    COMPATIBILITY WRAPPER: Provides create_websocket_manager for backward compatibility.

    DEPRECATED: Use WebSocketManager(user_context=user_context) directly instead.

    Args:
        user_context: Required UserExecutionContext for proper isolation

    Returns:
        WebSocketManager instance

    Raises:
        ValueError: If user_context is None (import-time initialization not allowed)
    """
    import warnings
    warnings.warn(
        "create_websocket_manager is deprecated. Use WebSocketManager(user_context=user_context) directly.",
        DeprecationWarning,
        stacklevel=2
    )

    if user_context is None:
        # CRITICAL: Import-time initialization violates User Context Architecture
        raise ValueError(
            "WebSocket manager creation requires valid UserExecutionContext. "
            "Import-time initialization is prohibited. Use request-scoped factory pattern instead. "
            "See User Context Architecture documentation for proper implementation."
        )

    # PHASE 1 FIX: Use WebSocketManager directly with proper token generation
    # This ensures the SSOT authorization token is properly provided
    import asyncio
    import secrets
    # Use canonical import from websocket_manager.py (not unified_manager.py which has __all__ = [])

    # Since this is a sync function but the factory is async, we need to handle this properly
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If we're already in an async context, we can't use run_until_complete
            # This is a legacy compatibility issue - recommend using async version
            raise RuntimeError(
                "create_websocket_manager cannot be called from async context. "
                "Use 'get_websocket_manager(user_context)' instead."
            )
        else:
            return WebSocketManager(
                user_context=user_context,
                _ssot_authorization_token=secrets.token_urlsafe(32)
            )
    except RuntimeError:
        # No event loop running, create one
        return WebSocketManager(
            user_context=user_context,
            _ssot_authorization_token=secrets.token_urlsafe(32)
        )

# COORDINATION FIX: Remove redundant imports that create fragmentation
# Use direct imports for these instead:
# from netra_backend.app.websocket_core.canonical_import_patterns import get_websocket_manager
# from netra_backend.app.websocket_core.migration_adapter import get_legacy_websocket_manager
# from netra_backend.app.websocket_core.user_context_extractor import UserContextExtractor
# from netra_backend.app.websocket_core.context import WebSocketContext

# ISSUE #1176 PHASE 2: Minimal backward compatibility aliases only
# COORDINATION FIX: Reduce aliases to prevent import fragmentation
WebSocketEventEmitter = UnifiedWebSocketEmitter

# COORDINATION FIX: Remove handler imports that create fragmentation
# Use direct imports for handlers instead:
# from netra_backend.app.websocket_core.handlers import MessageRouter

# Auth imports removed - using SSOT unified_websocket_auth instead

# COORDINATION FIX: Remove types imports that create fragmentation
# Use direct imports for types instead:
# from netra_backend.app.websocket_core.types import WebSocketMessage

# COORDINATION FIX: Remove utility imports that create fragmentation
# Use direct imports for utilities instead:
# from netra_backend.app.websocket_core.unified_jwt_protocol_handler import extract_jwt_from_subprotocol
# from netra_backend.app.websocket_core.rate_limiter import RateLimiter
# from netra_backend.app.websocket_core.utils import WebSocketHeartbeat

# COORDINATION FIX: Remove state machine and queue imports that create fragmentation
# Use direct imports for these critical components instead:
# from netra_backend.app.websocket_core.connection_state_machine import ConnectionStateMachine
# from netra_backend.app.websocket_core.message_queue import MessageQueue
# from netra_backend.app.websocket_core.race_condition_prevention import RaceConditionDetector

# Critical events that MUST be preserved
CRITICAL_EVENTS = UnifiedWebSocketEmitter.CRITICAL_EVENTS

# ISSUE #1176 PHASE 2 COORDINATION FIX: Minimal __all__ exports to reduce fragmentation
# Goal: Force consumers to use canonical direct imports from specific modules
__all__ = [
    # MINIMAL EXPORTS: Only absolutely essential for backward compatibility
    "WebSocketManager",           # CANONICAL: websocket_manager.py
    "UnifiedWebSocketManager",    # CANONICAL: unified_manager.py
    "UnifiedWebSocketEmitter",    # CANONICAL: unified_emitter.py
    "WebSocketManagerProtocol",   # CANONICAL: protocols.py

    # REMEDIATION: Critical missing exports for test compatibility (Issue #1176 Phase 2 Fix)
    "create_server_message",      # CANONICAL: types.py
    "create_error_message",       # CANONICAL: types.py

    # ISSUE #1286 FIX: Add missing get_websocket_manager export for test compatibility
    "get_websocket_manager",      # CANONICAL: websocket_manager.py

    # ISSUE #1286 FIX: Add missing create_test_user_context export for test compatibility
    "create_test_user_context",   # CANONICAL: websocket_manager.py

    # Backward compatibility only - prefer direct imports
    "create_websocket_manager",

    # Backward compatibility alias (minimal)
    "WebSocketEventEmitter",

    # Constants
    "CRITICAL_EVENTS",
    
    # GOLDEN PATH PHASE 3: Mission critical test compatibility
    "get_websocket_manager",

    # NOTE: All other exports removed to eliminate import path fragmentation
    # COORDINATION FIX: Use direct imports for all other components:
    # from netra_backend.app.websocket_core.handlers import MessageRouter
    # from netra_backend.app.websocket_core.auth import WebSocketAuthenticator
    # from netra_backend.app.websocket_core.types import WebSocketMessage
    # from netra_backend.app.websocket_core.utils import WebSocketHeartbeat
    # from netra_backend.app.websocket_core.connection_state_machine import ConnectionStateMachine
    # etc.
]

# REMEDIATION: Conditionally add optional exports if available
# These components may not exist in all environments
_optional_exports = []
if ConnectionStateMachine is not None:
    _optional_exports.append("ConnectionStateMachine")
if MessageQueue is not None:
    _optional_exports.append("MessageQueue")
if websocket_manager is not None:
    _optional_exports.append("websocket_manager")
if get_connection_monitor is not None:
    _optional_exports.append("get_connection_monitor")
if get_websocket_manager is not None:
    _optional_exports.append("get_websocket_manager")
if WebSocketHeartbeat is not None:
    _optional_exports.append("WebSocketHeartbeat")

__all__.extend(_optional_exports)


# GOLDEN PATH PHASE 3 FIX: Export get_websocket_manager for mission critical tests
from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager

# Log consolidation
from shared.logging.unified_logging_ssot import get_logger
logger = get_logger(__name__)
logger.info("WebSocket SSOT loaded - CRITICAL SECURITY MIGRATION: Factory pattern available, singleton vulnerabilities mitigated")
