"""Production-ready tool dispatcher with unified architecture.

MIGRATION COMPLETED: Now using UnifiedToolDispatcher as single source of truth.

The following implementations have been consolidated:
- tool_dispatcher_core.py → UnifiedToolDispatcher
- request_scoped_tool_dispatcher.py → UnifiedToolDispatcher  
- unified_tool_execution.py → integrated into UnifiedToolDispatcher
- websocket_tool_enhancement.py → replaced by ToolEventBus

ARCHITECTURE IMPROVEMENTS:
✅ Single source of truth eliminates duplication
✅ Request-scoped isolation by default with clear warnings for global usage  
✅ Clean separation of concerns (registry, permissions, events, execution)
✅ Integrated WebSocket event bus replaces adapter patterns
✅ Comprehensive permission layer with RBAC and rate limiting
✅ Enhanced security boundaries and audit logging

USAGE PATTERNS:
- RECOMMENDED: UnifiedToolDispatcherFactory.create_request_scoped()
- LEGACY: UnifiedToolDispatcherFactory.create_legacy_global() (emits warnings)
"""

import warnings
from typing import List, Optional

from langchain_core.tools import BaseTool

from netra_backend.app.agents.production_tool import ProductionTool, ToolExecuteResponse
from netra_backend.app.agents.tool_dispatcher_unified import (
    UnifiedToolDispatcher,
    UnifiedToolDispatcherFactory,
    ToolDispatchRequest,
    ToolDispatchResponse,
    create_request_scoped_tool_dispatcher,
    request_scoped_tool_dispatcher_context,
    create_legacy_tool_dispatcher
)

# Backward compatibility aliases - now using unified implementation
ToolDispatcher = UnifiedToolDispatcher

# Factory methods for different usage patterns
def create_tool_dispatcher(
    tools: List[BaseTool] = None,
    websocket_bridge = None,
    permission_service = None
) -> UnifiedToolDispatcher:
    """Create legacy global tool dispatcher (DEPRECATED).
    
    WARNING: This creates a global dispatcher that may cause isolation issues.
    Use create_request_scoped_tool_dispatcher() for new code.
    
    Args:
        tools: List of tools to register initially
        websocket_bridge: Legacy WebSocket bridge (DEPRECATED)
        permission_service: Permission service for security
        
    Returns:
        UnifiedToolDispatcher: Global dispatcher instance (with warnings)
    """
    warnings.warn(
        "create_tool_dispatcher() creates global state and may cause isolation issues. "
        "Use create_request_scoped_tool_dispatcher() for new code.",
        DeprecationWarning,
        stacklevel=2
    )
    return create_legacy_tool_dispatcher(tools, websocket_bridge, permission_service)

# Export public interfaces with clear migration path
__all__ = [
    # Backward compatibility (shows warnings for legacy usage)
    "ToolDispatcher", 
    "create_tool_dispatcher",
    
    # Modern unified implementation (RECOMMENDED)
    "UnifiedToolDispatcher",
    "UnifiedToolDispatcherFactory", 
    "create_request_scoped_tool_dispatcher",
    "request_scoped_tool_dispatcher_context",
    
    # Models and types
    "ToolDispatchRequest", 
    "ToolDispatchResponse", 
    "ProductionTool", 
    "ToolExecuteResponse"
]

# Migration guidance notice
def _emit_migration_notice():
    """Emit informational notice about successful migration."""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(
        "✅ Tool dispatcher consolidation complete. "
        "Using UnifiedToolDispatcher as single source of truth. "
        "Legacy global patterns will emit deprecation warnings."
    )

# Emit migration notice on module import  
_emit_migration_notice()