"""
WebSocket Supervisor Factory - WebSocket-Specific Patterns

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Development Velocity & Multi-User Support
- Value Impact: Enables proper WebSocket supervisor isolation without mock objects
- Strategic Impact: Provides clean WebSocket patterns for real-time AI interactions

This module provides WebSocket-specific supervisor factory functions that work
with honest WebSocket contexts instead of mock HTTP Request objects.

Key Features:
- Uses WebSocketContext instead of mock Request objects
- Delegates to core supervisor creation logic for consistency
- Provides WebSocket-specific validation and error handling
- Maintains proper connection lifecycle management
- Registry cleanup on WebSocket disconnect to prevent resource leaks

CRITICAL FIX: This module now includes proper registry cleanup to prevent
the "modelmetaclass already registered" error by cleaning up tool registries
when WebSocket connections are closed.
"""

from typing import Optional, TYPE_CHECKING, Dict, Set
import weakref
import threading

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from netra_backend.app.core.supervisor_factory import create_supervisor_core
from netra_backend.app.websocket_core.context import WebSocketContext
from netra_backend.app.logging_config import central_logger

if TYPE_CHECKING:
    from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent

logger = central_logger.get_logger(__name__)

# CRITICAL FIX: Global registry tracking for cleanup
# This prevents the "modelmetaclass already registered" error by tracking
# and cleaning up tool registries when WebSocket connections close
_connection_registries: Dict[str, Set[weakref.ref]] = {}
_connection_lock = threading.Lock()


async def get_websocket_scoped_supervisor(
    context: WebSocketContext,
    db_session: AsyncSession,
    app_state = None  # Optional app state for component access
) -> "SupervisorAgent":
    """Create supervisor specifically for WebSocket connections.
    
    This function creates a SupervisorAgent instance specifically for WebSocket
    connections using honest WebSocket context instead of mock HTTP Request objects.
    It delegates to the core supervisor creation logic for consistency.
    
    CRITICAL: This function eliminates the anti-pattern of creating mock Request
    objects for WebSocket connections. The WebSocketContext is honest about what
    it represents and provides all necessary information for supervisor creation.
    
    Args:
        context: WebSocketContext containing connection info and user identifiers
        db_session: Connection-scoped database session
        app_state: Optional app state object for accessing shared components
        
    Returns:
        SupervisorAgent: Isolated supervisor instance for this WebSocket connection
        
    Raises:
        HTTPException: If supervisor creation fails
        ValueError: If context validation fails
        
    Note:
        The database session is expected to be managed by the calling code.
        This function does not create or close sessions - it uses the provided
        session and delegates lifecycle management to the caller.
    """
    try:
        # Validate WebSocket context is ready for processing
        context.validate_for_message_processing()
        
        logger.debug(
            f"Creating WebSocket-scoped supervisor for connection {context.connection_id}, "
            f"user {context.user_id}, thread {context.thread_id}"
        )
        
        # Get required components for supervisor creation
        # SSOT FIX: Create user context from WebSocket context for LLM isolation
        from netra_backend.app.services.user_execution_context import UserExecutionContext
        user_context = UserExecutionContext(
            user_id=context.user_id,
            thread_id=context.thread_id,
            session_id=context.connection_id  # Use connection_id as session
        )
        components = await _get_websocket_supervisor_components(app_state, user_context)
        
        # Update activity timestamp
        context.update_activity()
        
        # Handle UserContext-based tool_dispatcher creation if needed
        tool_dispatcher = components.get("tool_dispatcher")
        
        if tool_dispatcher is None and "tool_classes" in components:
            # Create UserContext-based tool_dispatcher
            logger.debug("Creating UserContext-based tool_dispatcher for WebSocket")
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcher
            
            # Create user execution context for tool dispatcher
            user_context = UserExecutionContext(
                user_id=context.user_id,
                thread_id=context.thread_id,
                run_id=context.run_id,
                websocket_client_id=context.connection_id,
                db_session=db_session
            )
            
            # Create tool dispatcher using factory pattern
            tool_dispatcher = await UnifiedToolDispatcher.create_for_user(
                user_context=user_context,
                websocket_bridge=components["websocket_bridge"],
                tools=components["tool_classes"]
            )
            logger.info(f"Created UserContext tool_dispatcher for user {context.user_id}")
        
        # Delegate to core supervisor creation logic
        supervisor = await create_supervisor_core(
            user_id=context.user_id,
            thread_id=context.thread_id,
            run_id=context.run_id,
            db_session=db_session,
            websocket_client_id=context.connection_id,
            llm_client=components["llm_client"],
            websocket_bridge=components["websocket_bridge"],
            tool_dispatcher=tool_dispatcher,  # Now properly created or legacy
            tool_classes=components.get("tool_classes")  # Pass for UserContext pattern
        )
        
        # CRITICAL FIX: Track registries for cleanup on disconnect
        if tool_dispatcher and hasattr(tool_dispatcher, 'registry'):
            _track_registry_for_cleanup(context.connection_id, tool_dispatcher.registry)
        
        logger.info(
            f"✅ Created WebSocket-scoped SupervisorAgent: "
            f"connection={context.connection_id}, user={context.user_id}, "
            f"thread={context.thread_id}, run={context.run_id}"
        )
        
        return supervisor
        
    except ValueError as e:
        # Context validation errors
        logger.error(f"WebSocket context validation failed: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid WebSocket context: {str(e)}"
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
        
    except Exception as e:
        logger.error(f"Failed to create WebSocket-scoped supervisor: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create WebSocket supervisor: {str(e)}"
        )


async def _get_websocket_supervisor_components(app_state = None, user_context = None) -> dict:
    """Get required components for WebSocket supervisor creation.
    
    SSOT MIGRATION: Updated to use factory pattern with user isolation.
    This internal function retrieves all the components needed to create a
    WebSocket supervisor. It handles both cases where app_state is provided
    (normal operation) and where it's not (testing/standalone usage).
    
    Args:
        app_state: Optional FastAPI app state object
        user_context: Optional UserExecutionContext for user-scoped operations
        
    Returns:
        dict: Dictionary containing required components
        
    Raises:
        HTTPException: If required components are not available
    """
    components = {}
    
    try:
        # Get LLM client - SSOT FIX: Use factory pattern with user isolation
        from netra_backend.app.llm.client_unified import ResilientLLMClient
        from netra_backend.app.llm.llm_manager import create_llm_manager
        llm_manager = create_llm_manager(user_context)  # Create user-isolated instance
        components["llm_client"] = ResilientLLMClient(llm_manager)
        
    except Exception as e:
        logger.error(f"Failed to get LLM client for WebSocket supervisor: {e}")
        raise HTTPException(
            status_code=500,
            detail="LLM client not available for WebSocket operations"
        )
    
    try:
        # Get WebSocket bridge with fallback path resolution
        websocket_bridge = None
        
        if app_state:
            # Primary path: app_state.websocket_bridge (created by startup alias)
            if hasattr(app_state, 'websocket_bridge') and app_state.websocket_bridge:
                websocket_bridge = app_state.websocket_bridge
                logger.debug("Using primary WebSocket bridge path: app_state.websocket_bridge")
            # Fallback path: app_state.agent_websocket_bridge (original startup location)
            elif hasattr(app_state, 'agent_websocket_bridge') and app_state.agent_websocket_bridge:
                websocket_bridge = app_state.agent_websocket_bridge
                logger.debug("Using fallback WebSocket bridge path: app_state.agent_websocket_bridge")
        
        if websocket_bridge:
            components["websocket_bridge"] = websocket_bridge
        else:
            # Final check - if still no bridge found
            if "websocket_bridge" not in components:
                # SECURITY FIX: Remove unsafe singleton fallback to prevent user data leakage
                # The supervisor factory should not use singleton WebSocket managers
                bridge_paths_checked = []
                if app_state:
                    if hasattr(app_state, 'websocket_bridge'):
                        bridge_paths_checked.append(f"websocket_bridge={getattr(app_state, 'websocket_bridge', 'missing')}")
                    if hasattr(app_state, 'agent_websocket_bridge'):
                        bridge_paths_checked.append(f"agent_websocket_bridge={getattr(app_state, 'agent_websocket_bridge', 'missing')}")
                
                logger.error(
                    "WebSocket bridge not available for supervisor creation - "
                    f"app_state paths checked: {bridge_paths_checked or 'no app_state provided'}"
                )
                raise HTTPException(
                    status_code=500,
                    detail="WebSocket bridge not configured - app_state.websocket_bridge or app_state.agent_websocket_bridge is required"
                )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get WebSocket bridge: {e}")
        raise HTTPException(
            status_code=500,
            detail="WebSocket bridge not available"
        )
    
    # CRITICAL FIX: Handle UserContext-based factory pattern for tool_dispatcher
    # The system has migrated from singleton to per-user factory pattern
    # tool_dispatcher is now created per-user via UserExecutionContext
    try:
        # Check if we're using the new UserContext-based pattern
        if app_state and hasattr(app_state, 'tool_classes') and app_state.tool_classes:
            # UserContext-based pattern - tool_dispatcher created per-request
            # We'll pass None and let create_supervisor_core handle creation
            logger.debug("Using UserContext-based tool dispatcher pattern")
            components["tool_dispatcher"] = None  # Will be created per-user
            components["tool_classes"] = app_state.tool_classes  # Pass classes for creation
            
        elif app_state and hasattr(app_state, 'agent_supervisor'):
            # Legacy singleton pattern fallback
            legacy_supervisor = app_state.agent_supervisor
            if legacy_supervisor and hasattr(legacy_supervisor, 'tool_dispatcher'):
                logger.warning("Using legacy singleton tool_dispatcher - migration needed")
                components["tool_dispatcher"] = legacy_supervisor.tool_dispatcher
            else:
                # Legacy supervisor exists but no tool_dispatcher
                logger.debug("Legacy supervisor exists but tool_dispatcher is None (UserContext pattern)")
                components["tool_dispatcher"] = None
                
        else:
            # No tool configuration available
            logger.error("Neither tool_classes nor legacy supervisor available")
            raise HTTPException(
                status_code=500,
                detail="Tool dispatcher configuration not available"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get tool dispatcher configuration: {e}")
        raise HTTPException(
            status_code=500,
            detail="Tool dispatcher configuration not available"
        )
    
    # Validate required components (tool_dispatcher can be None for UserContext pattern)
    required_components = ["llm_client", "websocket_bridge"]
    for component_name in required_components:
        if component_name not in components or components[component_name] is None:
            logger.error(f"Required component {component_name} is missing or None")
            raise HTTPException(
                status_code=500,
                detail=f"Required component {component_name} not available"
            )
    
    # Special handling for tool_dispatcher - it can be None for UserContext pattern
    if "tool_dispatcher" not in components:
        # Ensure we have tool_classes for UserContext pattern
        if "tool_classes" not in components or not components["tool_classes"]:
            logger.error("Neither tool_dispatcher nor tool_classes available")
            raise HTTPException(
                status_code=500,
                detail="Tool dispatcher or tool classes configuration required"
            )
    
    logger.debug("Successfully retrieved all components for WebSocket supervisor creation")
    return components


async def create_websocket_supervisor_with_validation(
    context: WebSocketContext,
    db_session: AsyncSession,
    app_state = None,
    validate_connection: bool = True
) -> "SupervisorAgent":
    """Create WebSocket supervisor with additional validation and error handling.
    
    This is an enhanced version of get_websocket_scoped_supervisor that provides
    additional validation and error handling specifically for WebSocket scenarios.
    
    Args:
        context: WebSocketContext containing connection info
        db_session: Connection-scoped database session
        app_state: Optional app state for component access
        validate_connection: Whether to validate connection is still active
        
    Returns:
        SupervisorAgent: Validated supervisor instance
        
    Raises:
        HTTPException: If validation or creation fails
    """
    try:
        # Additional WebSocket-specific validations
        if validate_connection and not context.is_active:
            logger.warning(f"Creating supervisor for inactive WebSocket connection {context.connection_id}")
            # Don't fail - connection might have been closed but we still need to process
        
        # Check for stale connections
        from datetime import datetime, timedelta
        age = datetime.utcnow() - context.connected_at
        if age > timedelta(hours=24):  # 24 hour threshold
            logger.warning(
                f"Creating supervisor for very old WebSocket connection: "
                f"{context.connection_id} (age: {age})"
            )
        
        # Create supervisor using standard function
        supervisor = await get_websocket_scoped_supervisor(context, db_session, app_state)
        
        # Additional post-creation validation
        if not supervisor:
            raise ValueError("Supervisor creation returned None")
        
        return supervisor
        
    except Exception as e:
        logger.error(f"Enhanced WebSocket supervisor creation failed: {e}", exc_info=True)
        raise


# Alias for backward compatibility
create_websocket_supervisor = get_websocket_scoped_supervisor


def get_websocket_supervisor_health() -> dict:
    """Get health status of WebSocket supervisor factory components.
    
    Returns:
        dict: Health status information for diagnostics
    """
    try:
        from netra_backend.app.core.supervisor_factory import get_supervisor_health_info
        
        # Get core supervisor health
        core_health = get_supervisor_health_info()
        
        # Add WebSocket-specific checks
        websocket_health = {
            "websocket_manager_available": False,
            "websocket_bridge_available": False
        }
        
        try:
            # SECURITY FIX: Test factory pattern instead of unsafe singleton
            # Health check should verify the secure factory pattern is working
            from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketManagerFactory
            
            # Test that factory pattern is available (doesn't require user context for health check)
            factory_available = WebSocketManagerFactory is not None
            websocket_health["websocket_factory_available"] = factory_available
            websocket_health["websocket_manager_available"] = factory_available  # Legacy compatibility
            
            # Note: Cannot test bridge availability without user context in health check
            # This is by design for security - bridges are user-scoped
            websocket_health["websocket_bridge_available"] = "requires_user_context"
            
        except Exception as e:
            websocket_health["websocket_factory_error"] = str(e)
            websocket_health["websocket_manager_available"] = False
        
        # Combine health information
        return {
            "websocket_supervisor_factory": {
                "status": "healthy" if core_health["components_valid"] and websocket_health["websocket_manager_available"] else "degraded",
                **core_health,
                **websocket_health
            }
        }
        
    except Exception as e:
        return {
            "websocket_supervisor_factory": {
                "status": "unhealthy",
                "error": str(e)
            }
        }


def _track_registry_for_cleanup(connection_id: str, registry) -> None:
    """Track registry for cleanup when WebSocket connection closes.
    
    CRITICAL FIX: This prevents the "modelmetaclass already registered" error
    by tracking tool registries associated with WebSocket connections and
    cleaning them up when connections close.
    
    Args:
        connection_id: WebSocket connection ID
        registry: Registry instance to track
    """
    global _connection_registries, _connection_lock
    
    try:
        with _connection_lock:
            if connection_id not in _connection_registries:
                _connection_registries[connection_id] = set()
            
            # Use weak reference to avoid memory leaks
            registry_ref = weakref.ref(registry)
            _connection_registries[connection_id].add(registry_ref)
            
            logger.debug(f"🔍 Tracking registry for connection {connection_id}")
            
    except Exception as e:
        logger.error(f"Failed to track registry for cleanup: {e}")


def cleanup_websocket_registries(connection_id: str) -> None:
    """Clean up tool registries for a WebSocket connection.
    
    CRITICAL FIX: Call this function when a WebSocket connection closes
    to prevent the "modelmetaclass already registered" error on reconnection.
    
    Args:
        connection_id: WebSocket connection ID to clean up
    """
    global _connection_registries, _connection_lock
    
    try:
        with _connection_lock:
            if connection_id not in _connection_registries:
                logger.debug(f"No registries to clean up for connection {connection_id}")
                return
            
            registries_to_clean = _connection_registries[connection_id]
            cleaned_count = 0
            
            for registry_ref in registries_to_clean.copy():
                registry = registry_ref()  # Get the actual registry from weak reference
                if registry is not None:
                    try:
                        # Clear the registry
                        registry.clear()
                        cleaned_count += 1
                        logger.debug(f"🧹 Cleaned registry {registry.name}")
                    except Exception as e:
                        logger.warning(f"Failed to clean registry {getattr(registry, 'name', 'unknown')}: {e}")
                else:
                    # Registry was already garbage collected
                    registries_to_clean.discard(registry_ref)
            
            # Remove the connection from tracking
            del _connection_registries[connection_id]
            
            logger.info(f"✅ Cleaned up {cleaned_count} registries for WebSocket connection {connection_id}")
            
    except Exception as e:
        logger.error(f"Failed to cleanup registries for connection {connection_id}: {e}")


def get_registry_cleanup_status() -> dict:
    """Get status of registry cleanup system.
    
    Returns:
        dict: Status information for diagnostics
    """
    global _connection_registries, _connection_lock
    
    try:
        with _connection_lock:
            active_connections = len(_connection_registries)
            total_tracked_registries = sum(len(registries) for registries in _connection_registries.values())
            
            # Check for dead references
            dead_refs = 0
            for connection_id, registries in _connection_registries.items():
                for registry_ref in registries.copy():
                    if registry_ref() is None:
                        dead_refs += 1
                        registries.discard(registry_ref)
            
            return {
                "active_connections": active_connections,
                "total_tracked_registries": total_tracked_registries,
                "dead_references_cleaned": dead_refs,
                "status": "healthy" if active_connections < 1000 else "warning"  # Warn if too many connections
            }
            
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }