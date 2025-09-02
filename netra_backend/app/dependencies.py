from typing import TYPE_CHECKING, Annotated, AsyncGenerator, Optional
from contextlib import asynccontextmanager
import uuid

from fastapi import Depends, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

# Import from the single source of truth for database sessions
from netra_backend.app.database import get_db

from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.logging_config import central_logger
from netra_backend.app.services.security_service import SecurityService
from netra_backend.app.websocket_core import get_websocket_manager

# NEW: Split architecture imports
from netra_backend.app.agents.supervisor.user_execution_context import (
    UserExecutionContext,
    validate_user_context
)
from netra_backend.app.agents.supervisor.agent_instance_factory import (
    get_agent_instance_factory,
    configure_agent_instance_factory
)
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge

# NEW: Factory pattern imports
from netra_backend.app.agents.supervisor.execution_factory import (
    ExecutionEngineFactory, 
    ExecutionFactoryConfig,
    UserExecutionContext as FactoryUserExecutionContext
)
from netra_backend.app.services.websocket_bridge_factory import (
    WebSocketBridgeFactory,
    WebSocketFactoryConfig,
    WebSocketConnectionPool
)
from netra_backend.app.services.factory_adapter import (
    FactoryAdapter,
    AdapterConfig,
    create_request_context
)

if TYPE_CHECKING:
    from netra_backend.app.agents.supervisor_consolidated import (
        SupervisorAgent as Supervisor,
    )
    from netra_backend.app.services.agent_service import AgentService
    from netra_backend.app.services.corpus_service import CorpusService
    from netra_backend.app.services.thread_service import ThreadService

logger = central_logger.get_logger(__name__)

def _validate_session_type(session) -> None:
    """Validate session is AsyncSession type."""
    if not isinstance(session, AsyncSession):
        logger.error(f"Invalid session type: {type(session)}")
        raise RuntimeError(f"Expected AsyncSession, got {type(session)}")
    logger.debug(f"Dependency injected session type: {type(session).__name__}")

async def get_db_dependency() -> AsyncGenerator[AsyncSession, None]:
    """Wrapper for database dependency with validation.
    
    Uses the single source of truth from netra_backend.app.database.
    """
    async for session in get_db():
        _validate_session_type(session)
        yield session

DbDep = Annotated[AsyncSession, Depends(get_db_dependency)]

def get_llm_manager(request: Request) -> LLMManager:
    return request.app.state.llm_manager

# Legacy compatibility - DEPRECATED: use get_db_dependency() instead
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """DEPRECATED: Legacy compatibility function for get_db_session.
    
    This function is deprecated. Use get_db_dependency() or DbDep type annotation instead.
    Kept for backward compatibility with existing routes.
    """
    async for session in get_db():
        yield session

def get_security_service(request: Request) -> SecurityService:
    logger.debug("Getting security service from app state")
    return request.app.state.security_service

LLMManagerDep = Annotated[LLMManager, Depends(get_llm_manager)]

def get_agent_supervisor(request: Request) -> "Supervisor":
    """Get agent supervisor from app state - LEGACY mode.
    
    DEPRECATED: This returns a global supervisor instance without user isolation.
    For new code, use get_user_supervisor_factory() to create per-request supervisors.
    
    The supervisor is initialized at startup with WebSocket manager,
    so it should already have WebSocket capabilities when retrieved here.
    """
    logger.warning("Using legacy get_agent_supervisor - user isolation NOT guaranteed!")
    supervisor = request.app.state.agent_supervisor
    
    # Verify supervisor has WebSocket capabilities
    if supervisor and hasattr(supervisor, 'agent_registry'):
        # Get WebSocket manager and ensure it's set on the agent registry
        websocket_manager = get_websocket_manager()
        if websocket_manager and hasattr(supervisor.agent_registry, 'set_websocket_manager'):
            # Ensure WebSocket manager is properly configured
            supervisor.agent_registry.set_websocket_manager(websocket_manager)
            logger.debug("Verified WebSocket manager is set on supervisor agent registry")
        else:
            logger.warning("WebSocket manager not available or supervisor lacks agent_registry")
    else:
        logger.warning("Supervisor lacks agent_registry - WebSocket events may not work")
    
    return supervisor


def create_user_execution_context(user_id: str,
                                  thread_id: str, 
                                  run_id: Optional[str] = None,
                                  db_session: Optional[AsyncSession] = None,
                                  websocket_connection_id: Optional[str] = None) -> UserExecutionContext:
    """Create UserExecutionContext for per-request isolation.
    
    This function is the recommended way to create user contexts for new requests.
    
    Args:
        user_id: Unique user identifier
        thread_id: Thread identifier for conversation
        run_id: Optional run identifier (auto-generated if not provided)
        db_session: Optional database session
        websocket_connection_id: Optional WebSocket connection identifier
        
    Returns:
        UserExecutionContext: Isolated context for the request
        
    Raises:
        HTTPException: If context creation fails
    """
    try:
        # Generate run_id if not provided
        if not run_id:
            run_id = str(uuid.uuid4())
        
        # Create user execution context
        user_context = UserExecutionContext.from_request(
            user_id=user_id,
            thread_id=thread_id,
            run_id=run_id,
            db_session=db_session,
            websocket_connection_id=websocket_connection_id
        )
        
        logger.info(f"Created UserExecutionContext for user {user_id}, run {run_id}")
        return user_context
        
    except Exception as e:
        logger.error(f"Failed to create UserExecutionContext: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create user execution context: {str(e)}"
        )


async def get_user_supervisor_factory(request: Request,
                                     user_id: str,
                                     thread_id: str,
                                     run_id: Optional[str] = None,
                                     db_session: AsyncSession = Depends(get_db_dependency)) -> "Supervisor":
    """Factory to create per-request SupervisorAgent with UserExecutionContext.
    
    This is the PREFERRED way to get a SupervisorAgent in the new split architecture.
    It creates a completely isolated supervisor instance for each request.
    
    Args:
        request: FastAPI request object
        user_id: User identifier from request
        thread_id: Thread identifier from request
        run_id: Optional run identifier (auto-generated if not provided)
        db_session: Request-scoped database session
        
    Returns:
        SupervisorAgent: Isolated supervisor instance for this request
        
    Raises:
        HTTPException: If supervisor creation fails
    """
    try:
        # Create UserExecutionContext for this request
        user_context = create_user_execution_context(
            user_id=user_id,
            thread_id=thread_id,
            run_id=run_id,
            db_session=db_session
        )
        
        # Get required components from app state
        llm_manager = get_llm_manager(request)
        
        # Get WebSocket bridge from app state
        websocket_bridge = getattr(request.app.state, 'websocket_bridge', None)
        if not websocket_bridge:
            logger.error("WebSocket bridge not available in app state")
            raise HTTPException(
                status_code=500,
                detail="WebSocket bridge not configured"
            )
        
        # Get tool dispatcher from legacy supervisor for now
        legacy_supervisor = request.app.state.agent_supervisor
        tool_dispatcher = legacy_supervisor.tool_dispatcher if legacy_supervisor else None
        if not tool_dispatcher:
            logger.error("Tool dispatcher not available")
            raise HTTPException(
                status_code=500,
                detail="Tool dispatcher not configured"
            )
        
        # Create isolated SupervisorAgent using factory method
        from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
        supervisor = await SupervisorAgent.create_with_user_context(
            llm_manager=llm_manager,
            websocket_bridge=websocket_bridge,
            tool_dispatcher=tool_dispatcher,
            user_context=user_context,
            db_session_factory=lambda: db_session
        )
        
        logger.info(f"✅ Created isolated SupervisorAgent for user {user_id}, run {run_id or 'auto'}")
        return supervisor
        
    except Exception as e:
        logger.error(f"Failed to create isolated SupervisorAgent: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create isolated supervisor: {str(e)}"
        )


# Type alias for the new isolated supervisor dependency
IsolatedSupervisorDep = Annotated["Supervisor", Depends(get_user_supervisor_factory)]

def get_agent_service(request: Request) -> "AgentService":
    """Get agent service from app state.
    
    CRITICAL: This service MUST be initialized during startup.
    If missing, it indicates a startup failure that should have halted the application.
    """
    if not hasattr(request.app.state, 'agent_service'):
        # This should NEVER happen with deterministic startup
        # If it does, it means startup failed but app continued (graceful mode bug)
        logger.critical("CRITICAL: agent_service not initialized - startup sequence failed!")
        raise RuntimeError(
            "CRITICAL STARTUP FAILURE: agent_service is not initialized. "
            "This indicates the application started in a degraded state. "
            "The application should use deterministic startup to prevent this."
        )
    
    agent_service = request.app.state.agent_service
    if agent_service is None:
        # Service was set but is None - also a critical failure
        logger.critical("CRITICAL: agent_service is None - initialization failed!")
        raise RuntimeError(
            "CRITICAL INITIALIZATION FAILURE: agent_service is None. "
            "Critical services must never be None."
        )
    
    return agent_service

def get_thread_service(request: Request) -> "ThreadService":
    """Get thread service from app state.
    
    CRITICAL: This service MUST be initialized during startup.
    """
    if not hasattr(request.app.state, 'thread_service'):
        logger.critical("CRITICAL: thread_service not initialized - startup sequence failed!")
        raise RuntimeError(
            "CRITICAL STARTUP FAILURE: thread_service is not initialized. "
            "This indicates the application started in a degraded state."
        )
    
    thread_service = request.app.state.thread_service
    if thread_service is None:
        logger.critical("CRITICAL: thread_service is None - initialization failed!")
        raise RuntimeError(
            "CRITICAL INITIALIZATION FAILURE: thread_service is None. "
            "Critical services must never be None."
        )
    
    return thread_service

def get_corpus_service(request: Request) -> "CorpusService":
    """Get corpus service from app state.
    
    CRITICAL: This service MUST be initialized during startup.
    """
    if not hasattr(request.app.state, 'corpus_service'):
        logger.critical("CRITICAL: corpus_service not initialized - startup sequence failed!")
        raise RuntimeError(
            "CRITICAL STARTUP FAILURE: corpus_service is not initialized. "
            "This indicates the application started in a degraded state."
        )
    
    corpus_service = request.app.state.corpus_service
    if corpus_service is None:
        logger.critical("CRITICAL: corpus_service is None - initialization failed!")
        raise RuntimeError(
            "CRITICAL INITIALIZATION FAILURE: corpus_service is None. "
            "Critical services must never be None."
        )
    
    return corpus_service

def get_message_handler_service(request: Request):
    """Get message handler service from app state or create one.
    
    DEPRECATED: This creates MessageHandlerService with global supervisor.
    For new code, create MessageHandlerService with isolated supervisor using
    get_user_supervisor_factory().
    """
    logger.warning("Using legacy get_message_handler_service - consider using isolated supervisor")
    
    # Try to get from app state first
    if hasattr(request.app.state, 'message_handler_service'):
        return request.app.state.message_handler_service
    
    # Create one using available dependencies
    from netra_backend.app.services.message_handlers import MessageHandlerService
    supervisor = get_agent_supervisor(request)
    thread_service = get_thread_service(request)
    
    # CRITICAL FIX: Include WebSocket manager to enable real-time agent events
    # This ensures WebSocket events work in all scenarios, not just direct WebSocket routes
    try:
        websocket_manager = get_websocket_manager()
        logger.info("Successfully injected WebSocket manager into MessageHandlerService via dependency injection")
        return MessageHandlerService(supervisor, thread_service, websocket_manager)
    except Exception as e:
        # Backward compatibility: if WebSocket manager isn't available, still work without it
        logger.warning(f"Failed to get WebSocket manager for MessageHandlerService: {e}, creating without WebSocket support")
        return MessageHandlerService(supervisor, thread_service)


async def get_isolated_message_handler_service(user_id: str,
                                              thread_id: str,
                                              run_id: Optional[str],
                                              request: Request,
                                              db_session: AsyncSession = Depends(get_db_dependency)):
    """Create MessageHandlerService with isolated supervisor for this request.
    
    This is the PREFERRED way to get MessageHandlerService in the new architecture.
    
    Args:
        user_id: User identifier from request
        thread_id: Thread identifier from request  
        run_id: Optional run identifier
        request: FastAPI request object
        db_session: Request-scoped database session
        
    Returns:
        MessageHandlerService: Service with isolated supervisor
    """
    try:
        # Get isolated supervisor for this request
        supervisor = await get_user_supervisor_factory(
            request=request,
            user_id=user_id,
            thread_id=thread_id,
            run_id=run_id,
            db_session=db_session
        )
        
        # Get thread service
        thread_service = get_thread_service(request)
        
        # Get WebSocket manager
        websocket_manager = get_websocket_manager()
        
        # Create MessageHandlerService with isolated components
        from netra_backend.app.services.message_handlers import MessageHandlerService
        message_service = MessageHandlerService(supervisor, thread_service, websocket_manager)
        
        logger.info(f"✅ Created isolated MessageHandlerService for user {user_id}")
        return message_service
        
    except Exception as e:
        logger.error(f"Failed to create isolated MessageHandlerService: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create isolated message handler: {str(e)}"
        )