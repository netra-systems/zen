"""
Core Supervisor Factory - Protocol-Agnostic Logic

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Development Velocity & Code Quality
- Value Impact: Eliminates code duplication between HTTP and WebSocket supervisor creation
- Strategic Impact: Creates shared, testable core logic for supervisor instantiation

This module contains the core supervisor creation logic that is shared between
HTTP request-scoped and WebSocket-scoped supervisor factories. By extracting
the common logic, we eliminate duplication and ensure consistent behavior
across both protocols.

Key Features:
- Protocol-agnostic supervisor creation
- Shared validation and error handling
- Consistent session lifecycle management
- Reusable across HTTP and WebSocket patterns
"""

from typing import Callable, Optional, TYPE_CHECKING
import asyncio

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from netra_backend.app.dependencies import get_user_execution_context
from netra_backend.app.logging_config import central_logger

if TYPE_CHECKING:
    from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
    from netra_backend.app.llm.client_unified import ResilientLLMClient

logger = central_logger.get_logger(__name__)


async def create_supervisor_core(
    user_id: str,
    thread_id: str,
    run_id: str,
    db_session: AsyncSession,
    websocket_client_id: Optional[str] = None,
    llm_client: Optional["ResilientLLMClient"] = None,
    websocket_bridge = None,
    tool_dispatcher = None,
    tool_classes = None  # Optional tool classes for UserContext pattern
) -> "SupervisorAgent":
    """Core supervisor creation logic - protocol agnostic.
    
    This function contains the shared logic for creating SupervisorAgent instances
    that is used by both HTTP and WebSocket supervisor factories. It handles all
    the common setup, validation, and component wiring.
    
    CRITICAL: This function ensures database sessions are NEVER stored globally.
    The supervisor is created with proper session lifecycle management.
    
    Args:
        user_id: Unique user identifier
        thread_id: Thread identifier for conversation routing
        run_id: Run identifier for this session
        db_session: Request/connection-scoped database session
        websocket_client_id: Optional WebSocket connection identifier
        llm_client: Optional LLM client (will get default if not provided)
        websocket_bridge: Optional WebSocket bridge (required for WebSocket functionality)
        tool_dispatcher: Optional tool dispatcher (required for agent operations)
        
    Returns:
        SupervisorAgent: Isolated supervisor instance with proper session lifecycle
        
    Raises:
        HTTPException: If supervisor creation fails
        RuntimeError: If database session validation fails
        
    Note:
        This function is protocol-agnostic - it doesn't care whether it's being
        called from an HTTP request or WebSocket connection. The calling code
        is responsible for providing the appropriate components.
    """
    try:
        # CRITICAL: Validate that session is not globally stored
        if hasattr(db_session, '_global_storage_flag') and db_session._global_storage_flag:
            logger.error("CRITICAL: Attempted to use globally stored session in supervisor creation")
            raise RuntimeError("Database sessions must be request/connection-scoped only")
        
        logger.debug(
            f"Creating protocol-agnostic supervisor for user {user_id}, "
            f"thread {thread_id}, run {run_id}, session {id(db_session)}"
        )
        
        # Get UserExecutionContext using session management for conversation continuity
        user_context = get_user_execution_context(
            user_id=user_id,
            thread_id=thread_id,
            run_id=run_id
        )
        
        # Get or validate LLM client - SSOT FIX: Use factory pattern with user isolation
        if not llm_client:
            from netra_backend.app.llm.client_unified import ResilientLLMClient
            from netra_backend.app.llm.llm_manager import create_llm_manager
            # Create user context for LLM isolation
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            user_context = UserExecutionContext(
                user_id=user_id,
                thread_id=thread_id,
                run_id=run_id,
                session_id=websocket_client_id
            )
            llm_manager = create_llm_manager(user_context)  # Create user-isolated instance
            llm_client = ResilientLLMClient(llm_manager)
        
        # Validate WebSocket bridge
        if not websocket_bridge:
            logger.error("WebSocket bridge not provided to core supervisor factory")
            raise HTTPException(
                status_code=500,
                detail="WebSocket bridge is required for supervisor creation"
            )
        
        # Handle tool dispatcher - can be None for UserContext pattern
        if not tool_dispatcher and not tool_classes:
            logger.warning(
                "Neither tool_dispatcher nor tool_classes provided - "
                "supervisor may have limited functionality"
            )
            # Tool dispatcher will be created within SupervisorAgent if tool_classes available
        
        # CRITICAL: Create session factory that returns the scoped session
        # This session will be automatically closed by the calling scope
        async def scoped_session_factory():
            """Returns the scoped session - never creates new sessions.
            
            This factory ensures the supervisor uses the same session that
            was created in the calling scope (HTTP request or WebSocket connection).
            The session lifecycle is managed by the calling code.
            """
            logger.debug(f"Returning scoped session {id(db_session)} to supervisor")
            return db_session
        
        # Create isolated SupervisorAgent using factory method
        from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
        
        # Extract LLM manager from client if needed
        if hasattr(llm_client, '_llm_manager'):
            llm_manager = llm_client._llm_manager
        else:
            # llm_client might already be an LLMManager
            from netra_backend.app.llm.llm_manager import LLMManager
            if isinstance(llm_client, LLMManager):
                llm_manager = llm_client
            else:
                # Create new LLM manager if needed - SSOT FIX: Use factory pattern
                user_context = UserExecutionContext(
                    user_id=user_id,
                    thread_id=thread_id,
                    run_id=run_id,
                    session_id=websocket_client_id
                )
                llm_manager = create_llm_manager(user_context)
        
        # Create supervisor with UserContext pattern
        supervisor = SupervisorAgent.create(
            llm_manager=llm_manager,
            websocket_bridge=websocket_bridge,
            tool_dispatcher=tool_dispatcher
        )
        
        # Store the user context for later use in execute()
        # The supervisor will create its own tool_dispatcher during execute() if not provided
        supervisor._pending_user_context = user_context
        supervisor._tool_classes = tool_classes  # Store for UserContext-based creation
        
        logger.info(
            f" PASS:  Created isolated SupervisorAgent via core factory: "
            f"user={user_id}, thread={thread_id}, run={run_id}"
        )
        return supervisor
        
    except Exception as e:
        logger.error(f"Failed to create supervisor via core factory: {e}", exc_info=True)
        
        # Re-raise HTTPExceptions as-is
        if isinstance(e, HTTPException):
            raise
        
        # Wrap other exceptions in HTTPException
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create supervisor: {str(e)}"
        )


def validate_supervisor_components(
    llm_client = None,
    websocket_bridge = None,
    tool_dispatcher = None
) -> tuple[bool, list[str]]:
    """Validate that required supervisor components are available.
    
    This utility function validates that all required components for supervisor
    creation are properly configured. Useful for health checks and diagnostics.
    
    Args:
        llm_client: LLM client to validate
        websocket_bridge: WebSocket bridge to validate
        tool_dispatcher: Tool dispatcher to validate
        
    Returns:
        tuple: (is_valid, list_of_missing_components)
    """
    missing_components = []
    
    if not llm_client:
        try:
            from netra_backend.app.llm.client_unified import ResilientLLMClient
            from netra_backend.app.llm.llm_manager import create_llm_manager
            # SSOT FIX: Use factory pattern (no user context for validation)
            llm_manager = create_llm_manager(None)  # Create validation instance
            llm_client = ResilientLLMClient(llm_manager)
        except Exception as e:
            missing_components.append(f"llm_client: {e}")
    
    if not websocket_bridge:
        missing_components.append("websocket_bridge: not provided")
    
    if not tool_dispatcher:
        missing_components.append("tool_dispatcher: not provided")
    
    is_valid = len(missing_components) == 0
    return is_valid, missing_components


async def create_streaming_supervisor(
    user_id: str,
    thread_id: str,
    run_id: Optional[str] = None
) -> "SupervisorAgent":
    """Create supervisor for streaming endpoints without FastAPI request dependency.
    
    This function creates a supervisor for streaming endpoints that don't have access
    to FastAPI request objects. It handles all required dependencies internally and
    provides proper session lifecycle management.
    
    Business Value: Enables streaming chat functionality for investor demos ($120K+ MRR)
    
    Args:
        user_id: Unique user identifier
        thread_id: Thread identifier for conversation routing  
        run_id: Optional run identifier (auto-generated if not provided)
        
    Returns:
        SupervisorAgent: Isolated supervisor instance for streaming
        
    Raises:
        HTTPException: If supervisor creation fails
        RuntimeError: If required components are not available
    """
    try:
        # Generate run_id if not provided using SSOT pattern
        if not run_id:
            from shared.id_generation.unified_id_generator import UnifiedIdGenerator
            run_id = UnifiedIdGenerator.generate_base_id("run")
        
        logger.info(
            f"Creating streaming supervisor for user {user_id[:8]}..., "
            f"thread {thread_id[:8]}..., run {run_id[:8]}..."
        )
        
        # Create request-scoped database session
        from netra_backend.app.dependencies import get_request_scoped_db_session
        
        # Use async context manager to get database session
        async for db_session in get_request_scoped_db_session():
            try:
                # Get required components for supervisor creation
                
                # Create LLM client - SSOT FIX: Use factory pattern with user isolation
                from netra_backend.app.llm.client_unified import ResilientLLMClient
                from netra_backend.app.llm.llm_manager import create_llm_manager
                from netra_backend.app.services.user_execution_context import UserExecutionContext
                user_context = UserExecutionContext(
                    user_id=user_id,
                    thread_id=thread_id,
                    run_id=run_id
                )
                llm_manager = create_llm_manager(user_context)
                llm_client = ResilientLLMClient(llm_manager)
                
                # Create WebSocket bridge using factory pattern
                from netra_backend.app.services.user_execution_context import UserExecutionContext
                
                user_context = UserExecutionContext.from_request(
                    user_id=user_id,
                    thread_id=thread_id,
                    run_id=run_id
                )
                
                from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager
                websocket_manager = await create_websocket_manager(user_context)
                
                # Get tool classes for UserContext pattern
                from netra_backend.app.tools import get_default_tool_classes
                tool_classes = get_default_tool_classes()
                
                # Create supervisor using core factory
                supervisor = await create_supervisor_core(
                    user_id=user_id,
                    thread_id=thread_id,
                    run_id=run_id,
                    db_session=db_session,
                    websocket_client_id=user_context.websocket_client_id,
                    llm_client=llm_client,
                    websocket_bridge=websocket_manager,
                    tool_dispatcher=None,  # Will be created via UserContext pattern
                    tool_classes=tool_classes
                )
                
                logger.info(
                    f" PASS:  Created streaming supervisor for user {user_id[:8]}..., "
                    f"run {run_id[:8]}..."
                )
                return supervisor
                
            except Exception as e:
                logger.error(f"Failed to create streaming supervisor: {e}", exc_info=True)
                raise
            
    except Exception as e:
        logger.error(f"Failed to create streaming supervisor for user {user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create streaming supervisor: {str(e)}"
        )


def get_supervisor_health_info() -> dict:
    """Get health information about supervisor factory components.
    
    Returns:
        dict: Health information about components required for supervisor creation
    """
    try:
        is_valid, missing_components = validate_supervisor_components()
        
        return {
            "status": "healthy" if is_valid else "degraded",
            "components_valid": is_valid,
            "missing_components": missing_components,
            "factory_available": True
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "components_valid": False,
            "error": str(e),
            "factory_available": False
        }