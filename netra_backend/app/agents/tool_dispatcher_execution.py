"""Tool execution engine for the dispatcher - MIGRATED TO USEREXECUTIONENGINE (Issue #1146).

PHASE 2 MIGRATION: This module now delegates to UserExecutionEngine instead of UnifiedToolExecutionEngine.
This provides the ToolExecutionEngine interface compatibility while using the SSOT execution engine.

Business Value: Eliminates ToolExecutionEngine fragmentation, maintains Golden Path functionality.
"""
from typing import TYPE_CHECKING, Any, Dict, Optional

from netra_backend.app.agents.production_tool import ProductionTool
from netra_backend.app.schemas.agent_models import DeepAgentState  # DEPRECATED - for compatibility only
from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.tool import (
    SimpleToolPayload,
    ToolExecuteResponse,
    ToolExecutionEngineInterface,
    ToolInput,
    ToolResult,
    ToolStatus,
)

if TYPE_CHECKING:
    from netra_backend.app.agents.tool_dispatcher_core import ToolDispatchResponse
    # ISSUE #1144 FIX: Use canonical SSOT import path
    from netra_backend.app.websocket_core.websocket_manager import WebSocketManager

logger = central_logger.get_logger(__name__)

class ToolExecutionEngine(ToolExecutionEngineInterface):
    """Handles tool execution with proper error handling - MIGRATED to UserExecutionEngine delegation.
    
    Issue #1146 Phase 2: This class now creates and delegates to UserExecutionEngine
    instead of UnifiedToolExecutionEngine, providing SSOT consolidation while maintaining
    backward compatibility for existing code that expects this interface.
    """
    
    def __init__(self, websocket_manager: Optional['WebSocketManager'] = None):
        """Initialize with UserExecutionEngine delegation pattern.
        
        Issue #1146 Phase 2: Instead of creating UnifiedToolExecutionEngine, this now
        defers creation of UserExecutionEngine until a user context is available,
        providing proper user isolation and SSOT compliance.
        """
        self._websocket_manager = websocket_manager
        self._user_execution_engine = None  # Deferred creation with user context
        
        # Store migration metadata for debugging
        self._migrated = True
        self._migration_issue = "#1146"
        self._ssot_target = "UserExecutionEngine"
        self._phase = "Phase 2 - ToolExecutionEngine consolidation"

        # MIGRATION HELPER: Updated to reflect UserExecutionEngine migration
        self._migration_helper = {
            'migrated_to': 'UserExecutionEngine with ToolExecutionEngineInterface',
            'new_pattern': 'await UserExecutionEngine.create_execution_engine(user_context, registry, websocket_bridge)',
            'best_practice': 'Use UserExecutionEngine directly with user context for proper isolation',
            'migration_guide': 'Issue #1146 ToolExecutionEngine consolidation to UserExecutionEngine',
            'backward_compatibility': 'This class provides interface compatibility during transition'
        }
        
        logger.info(f" MIGRATION:  ToolExecutionEngine initialized with UserExecutionEngine delegation "
                   f"pattern (Issue #1146 Phase 2). WebSocket manager: {websocket_manager is not None}")
        
    async def _ensure_user_execution_engine(self, user_context=None):
        """Ensure UserExecutionEngine is created with proper user context.
        
        This method creates UserExecutionEngine when needed, providing proper user isolation.
        If no user context is provided, creates a fallback context for compatibility.
        """
        if self._user_execution_engine is not None:
            return self._user_execution_engine
            
        try:
            # Import required components
            # SSOT REMEDIATION Issue #1186: Use canonical imports
            from netra_backend.app.agents.canonical_imports import UserExecutionEngine
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType
            
            # Create user context if not provided (compatibility mode)
            if user_context is None:
                id_manager = UnifiedIDManager()
                user_context = UserExecutionContext(
                    user_id=id_manager.generate_id(IDType.USER, prefix="tool_exec"),
                    thread_id=id_manager.generate_id(IDType.THREAD, prefix="tool"),
                    run_id=id_manager.generate_id(IDType.EXECUTION, prefix="tool"),
                    request_id=id_manager.generate_id(IDType.REQUEST, prefix="tool"),
                    metadata={
                        'compatibility_mode': True,
                        'migration_issue': '#1146',
                        'created_for': 'tool_dispatcher_execution_compatibility'
                    }
                )
                logger.warning(f"Created fallback user context for ToolExecutionEngine compatibility: {user_context.user_id}")
            
            # Create UserExecutionEngine
            from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
            
            # Create WebSocket bridge if manager provided
            websocket_bridge = None
            if self._websocket_manager:
                websocket_bridge = AgentWebSocketBridge()
                websocket_bridge._websocket_manager = self._websocket_manager
                
            # Use UserExecutionEngine factory method for proper initialization
            self._user_execution_engine = await UserExecutionEngine.create_execution_engine(
                user_context=user_context,
                registry=None,  # Will be initialized by factory
                websocket_bridge=websocket_bridge
            )
            
            logger.info(f" PASS:  UserExecutionEngine created for ToolExecutionEngine delegation "
                       f"(user: {user_context.user_id}, Issue #1146 Phase 2)")
            
            return self._user_execution_engine
            
        except Exception as e:
            logger.error(f" ALERT:  Failed to create UserExecutionEngine for ToolExecutionEngine: {e}")
            raise RuntimeError(f"UserExecutionEngine creation failed during ToolExecutionEngine migration: {e}")
    
    async def execute_tool_with_input(self, tool_input: ToolInput, tool: Any, kwargs: Dict[str, Any]) -> ToolResult:
        """Execute tool and return typed result - delegates to UserExecutionEngine.
        
        Issue #1146 Phase 2: Now delegates to UserExecutionEngine instead of UnifiedToolExecutionEngine.
        """
        try:
            logger.debug(f" MIGRATION:  execute_tool_with_input: {tool_input.tool_name} via UserExecutionEngine")
            user_engine = await self._ensure_user_execution_engine()
            return await user_engine.execute_tool_with_input(tool_input, tool, kwargs)
        except Exception as e:
            logger.error(f" ALERT:  execute_tool_with_input delegation failed: {e}")
            raise
    
    async def execute_with_state(
        self,
        tool: Any,
        tool_name: str,
        parameters: Dict[str, Any],
        state: DeepAgentState,  # DEPRECATED - kept for compatibility
        run_id: str
    ) -> "ToolDispatchResponse":
        """Execute tool with state and comprehensive error handling - delegates to UserExecutionEngine.
        
        Issue #1146 Phase 2: Now delegates to UserExecutionEngine with security improvements.
        SECURITY: DeepAgentState parameter is deprecated but kept for compatibility.
        """
        try:
            logger.debug(f" MIGRATION:  execute_with_state: {tool_name} via UserExecutionEngine")
            user_engine = await self._ensure_user_execution_engine()
            
            # Delegate to UserExecutionEngine (which handles state security)
            result = await user_engine.execute_with_state(tool, tool_name, parameters, state, run_id)
            
            # Convert result to ToolDispatchResponse (maintain original interface)
            from netra_backend.app.agents.tool_dispatcher_core import ToolDispatchResponse
            if result.get("success"):
                return ToolDispatchResponse(
                    success=True,
                    result=result.get("result"),
                    metadata=result.get("metadata", {})
                )
            else:
                return ToolDispatchResponse(
                    success=False,
                    error=result.get("error"),
                    metadata=result.get("metadata", {})
                )
        except Exception as e:
            logger.error(f" ALERT:  execute_with_state delegation failed: {e}")
            # Return error ToolDispatchResponse
            from netra_backend.app.agents.tool_dispatcher_core import ToolDispatchResponse
            return ToolDispatchResponse(
                success=False,
                error=f"Tool execution failed: {str(e)}",
                metadata={"error_type": type(e).__name__, "migration_issue": "#1146"}
            )
    
    # Interface Implementation Method
    async def execute_tool(
        self, 
        tool_name: str, 
        parameters: Dict[str, Any]
    ) -> ToolExecuteResponse:
        """Execute a tool by name with parameters - delegates to UserExecutionEngine.
        
        Issue #1146 Phase 2: Now delegates to UserExecutionEngine for SSOT compliance.
        """
        try:
            logger.debug(f" MIGRATION:  execute_tool: {tool_name} via UserExecutionEngine")
            user_engine = await self._ensure_user_execution_engine()
            return await user_engine.execute_tool(tool_name, parameters)
        except Exception as e:
            logger.error(f" ALERT:  execute_tool delegation failed: {e}")
            raise