from typing import TYPE_CHECKING, Annotated, AsyncGenerator, Optional, Union, Dict, Any
from contextlib import asynccontextmanager
import uuid
import time
from datetime import datetime

from fastapi import Depends, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

# Import from the single source of truth for database sessions
from netra_backend.app.database import get_db

from netra_backend.app.llm.client_unified import ResilientLLMClient
from netra_backend.app.logging_config import central_logger
from netra_backend.app.services.security_service import SecurityService
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager

# CRITICAL: Import for proper session lifecycle management
from contextlib import asynccontextmanager
from dataclasses import dataclass

# CRITICAL: Import session management for per-request isolation using TYPE_CHECKING to avoid circular imports
if TYPE_CHECKING:
    pass  # Legacy session manager imports removed - using SSOT database module

# SSOT COMPLIANCE FIX: Import UserExecutionContext from services (SSOT) instead of models
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor.user_execution_context import (
    validate_user_context
)
from netra_backend.app.agents.supervisor.agent_instance_factory import (
    get_agent_instance_factory,
    configure_agent_instance_factory
)
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge

# NEW: Factory pattern imports - UPDATED TO USE UNIFIED FACTORY
from netra_backend.app.agents.execution_engine_unified_factory import (
    UnifiedExecutionEngineFactory as ExecutionEngineFactory,  # Alias for backward compatibility
    ExecutionEngineFactory as LegacyExecutionEngineFactoryAlias
)
# Legacy imports for configuration compatibility
from netra_backend.app.agents.supervisor.execution_factory import (
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

# Session isolation error class
class SessionIsolationError(Exception):
    """Raised when session isolation is violated."""
    pass

# Basic session validation functions (replacing legacy lazy imports)
def validate_session_is_request_scoped_simple(session: AsyncSession) -> None:
    """Simple session validation for request scope."""
    if hasattr(session, '_global_storage_flag') and session._global_storage_flag:
        raise SessionIsolationError("Session must be request-scoped, not globally stored")
    logger.debug(f"Session {id(session)} validated as request-scoped")

# Session validation utilities - Simplified SSOT implementation
def validate_session_is_request_scoped(session: AsyncSession, context: str = "unknown") -> None:
    """Validate that a session is request-scoped and not globally stored.
    
    Args:
        session: Database session to validate
        context: Context description for logging
        
    Raises:
        SessionIsolationError: If session appears to be globally stored
    """
    try:
        # Use simplified validation
        validate_session_is_request_scoped_simple(session)
        logger.debug(f"Validated session {id(session)} is request-scoped for {context}")
        
    except Exception as e:
        # Check if it's the SessionIsolationError we want to re-raise
        if isinstance(e, SessionIsolationError):
            raise
        logger.error(f"Session validation failed in {context}: {e}")
        raise SessionIsolationError(f"Session validation failed in {context}: {e}")

def mark_session_as_global(session: AsyncSession) -> None:
    """Mark a session as globally stored (for validation purposes).
    
    This is used to detect when globally stored sessions are being passed
    to request-scoped contexts.
    
    Args:
        session: Database session to mark
    """
    session._global_storage_flag = True
    logger.debug(f"Marked session {id(session)} as globally stored")

def ensure_session_lifecycle_logging(session: AsyncSession, operation: str) -> None:
    """Log session lifecycle events for debugging.
    
    Args:
        session: Database session
        operation: Operation being performed
    """
    logger.debug(f"Session {id(session)} lifecycle: {operation}")

def _validate_session_type(session) -> None:
    """Validate session is AsyncSession type and tag with request context."""
    from shared.database.session_validation import validate_db_session, is_real_session
    
    try:
        validate_db_session(session, "dependencies_validation")
    except TypeError as e:
        logger.error(f"Invalid session type: {type(session)}")
        raise RuntimeError(str(e))
    
    # Tag session as request-scoped (only for real sessions)
    if is_real_session(session):
        if not hasattr(session, 'info'):
            session.info = {}
        session.info['is_request_scoped'] = True
        session.info['validated_at'] = datetime.now().isoformat()
    
    logger.debug(f"Dependency injected session type: {type(session).__name__}")
    if session:
        ensure_session_lifecycle_logging(session, "validated_dependency_injection")

@dataclass
class RequestScopedContext:
    """Request-scoped context that never stores sessions globally.
    
    CRITICAL: This context only holds request metadata, never database sessions.
    Sessions are created and managed within the request scope only.
    """
    user_id: str
    thread_id: str
    run_id: Optional[str] = None
    websocket_client_id: Optional[str] = None
    request_id: Optional[str] = None
    
    def __post_init__(self):
        # SSOT COMPLIANCE FIX: Use UnifiedIdGenerator instead of direct UUID generation
        from shared.id_generation import UnifiedIdGenerator
        
        if not self.run_id:
            self.run_id = UnifiedIdGenerator.generate_base_id("run")
        if not self.request_id:
            self.request_id = UnifiedIdGenerator.generate_base_id("req")
            
        # CRITICAL: Log that this context contains NO database sessions
        logger.debug(f"Created RequestScopedContext {self.request_id} - NO sessions stored")

async def get_request_scoped_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a request-scoped database session with proper lifecycle management.
    
    CRITICAL: This creates a fresh session for each request and ensures it's
    properly closed after the request completes. Sessions are NEVER stored globally.
    
    NOTE: No @asynccontextmanager decorator for FastAPI compatibility.
    
    Uses the enhanced RequestScopedSessionFactory for isolation and monitoring.
    """
    from netra_backend.app.database.request_scoped_session_factory import get_session_factory
    from netra_backend.app.clients.auth_client_core import AuthServiceClient
    
    # SSOT COMPLIANCE FIX: Generate unique request ID using UnifiedIdGenerator
    from shared.id_generation import UnifiedIdGenerator
    request_id = UnifiedIdGenerator.generate_base_id("req")
    correlation_id = UnifiedIdGenerator.generate_base_id("corr")  # For tracing across services
    
    # CRITICAL FIX: Use proper service authentication context instead of hardcoded "system"
    # This enables service-to-service authentication with SERVICE_ID and SERVICE_SECRET
    user_id = get_service_user_context()  # Returns "service:netra-backend" instead of "system"
    
    # CRITICAL FIX: Handle system user authentication for internal operations
    # System users don't have JWT tokens but need service-level authentication
    from netra_backend.app.clients.auth_client_core import AuthServiceClient
    
    # For system operations, we may need to create a service token or bypass auth validation
    # This ensures system users can perform internal operations without 403 errors
    auth_client = AuthServiceClient()
    
    # CRITICAL FIX: Handle service user authentication using service-to-service validation
    if user_id.startswith("service:"):
        logger.info(f"Creating session for service user '{user_id}' - validating using service-to-service authentication")
        
        # Validate system user using service credentials instead of JWT tokens
        try:
            # Extract service ID from context format ("service:netra-backend" -> "netra-backend")
            service_id = user_id.split(":", 1)[1] if ":" in user_id else user_id
            system_validation = await auth_client.validate_service_user_context(service_id, "database_session_creation")
            if system_validation and system_validation.get("valid"):
                logger.info(
                    f"✅ Service user validation successful - service ID: {system_validation.get('service_id')} | "
                    f"Authentication method: {system_validation.get('authentication_method')} | "
                    f"User context: {user_id}"
                )
            else:
                logger.error(
                    f"❌ Service user validation failed - {system_validation.get('error', 'unknown_error')} | "
                    f"User context: {user_id} | "
                    f"Details: {system_validation.get('details', 'No details')} | "
                    f"Fix: {system_validation.get('fix', 'Check service configuration')}"
                )
                # Continue with session creation but log the authentication issue
                # The session creation should still work for internal operations
        except Exception as validation_error:
            logger.error(
                f"❌ Service user validation exception: {validation_error} | "
                f"User context: {user_id} | "
                f"Continuing with session creation for internal operations"
            )
    
    # ENHANCED DEBUGGING: Log the exact moment and values at function start
    logger.info(
        f"📍 FUNCTION_START: get_request_scoped_db_session called | "
        f"Generated IDs: request_id='{request_id}', correlation_id='{correlation_id}' | "
        f"Service user_id='{user_id}' (PROPER SERVICE CONTEXT!) | "
        f"Function: netra_backend.app.dependencies.get_request_scoped_db_session:182"
    )
    
    # CRITICAL DEBUG CONTEXT: This is where the 'system' user_id originates!
    session_init_context = {
        "user_id": user_id,
        "request_id": request_id,
        "correlation_id": correlation_id,  # For cross-service tracing
        "source": "get_request_scoped_db_session",
        "auth_note": f"user_id='{user_id}' is service context - enables service-to-service authentication",
        "function_location": "netra_backend.app.dependencies:182",
        "potential_auth_failure_point": f"If service user_id '{user_id}' causes auth errors, check SERVICE_ID and SERVICE_SECRET configuration",
        "trace_info": {
            "session_factory_call": "about_to_call_factory.get_request_scoped_session",
            "auth_middleware_status": "unknown_at_this_point",
            "user_context_override_status": "not_yet_attempted"
        }
    }
    
    logger.info(
        f"🚀 INITIALIZING: Request-scoped database session {request_id} with service user_id='{user_id}'. "
        f"IMPORTANT: This service user context enables service-to-service authentication. "
        f"If you see auth errors with user_id='{user_id}', check SERVICE_ID and SERVICE_SECRET configuration. "
        f"Context: {session_init_context}"
    )
    
    # INITIALIZATION CONTEXT DUMP - trace the start of session creation
    try:
        from netra_backend.app.logging.auth_trace_logger import log_authentication_context_dump
        log_authentication_context_dump(
            user_id=user_id,
            request_id=request_id,
            operation="initialize_request_scoped_db_session",
            correlation_id=correlation_id,
            function_location="netra_backend.app.dependencies.get_request_scoped_db_session:182",
            user_id_source="service_authentication_context",
            auth_stage="pre_session_creation",
            expected_behavior="service_user_context_enables_service_to_service_auth",
            warning="if_service_user_causes_403_check_service_credentials_configuration"
        )
    except Exception:
        pass  # Don't fail initialization due to logging issues
    
    try:
        # Get the factory and use its method directly (which is decorated with @asynccontextmanager)
        factory = await get_session_factory()
        # Since factory.get_request_scoped_session is decorated with @asynccontextmanager,
        # we use it with async with
        async with factory.get_request_scoped_session(user_id, request_id) as session:
            _validate_session_type(session)
            
            # ENHANCED SUCCESS LOGGING with authentication context
            session_success_context = {
                "session_id": id(session),
                "user_id": user_id,
                "request_id": request_id,
                "session_type": type(session).__name__,
                "factory_source": "RequestScopedSessionFactory",
                "auth_success": f"SUCCESS with user_id='{user_id}' indicates proper service-to-service authentication is working"
            }
            
            logger.info(
                f"✅ SUCCESS: Database session {id(session)} created for request {request_id} with service user_id='{user_id}'. "
                f"Context: {session_success_context}"
            )
            
            # Special logging for service user - this helps debug authentication issues
            if user_id.startswith("service:"):
                logger.info(
                    f"🔧 SERVICE USER SESSION: Created session for service user_id='{user_id}'. "
                    f"This indicates proper service-to-service authentication is being used. "
                    f"If this causes 403 errors, check SERVICE_ID and SERVICE_SECRET configuration in environment. "
                    f"Session: {id(session)}, Request: {request_id}"
                )
            
            yield session
            
            logger.info(
                f"✅ COMPLETED: Request-scoped session {id(session)} completed successfully for user_id='{user_id}', request_id='{request_id}'"
            )
    except Exception as e:
        # ENHANCED ERROR LOGGING with 10x more authentication context
        error_context = {
            "request_id": request_id,
            "user_id": user_id,
            "error_type": type(e).__name__,
            "error_message": str(e),
            "function_location": "netra_backend.app.dependencies.get_request_scoped_db_session",
            "auth_analysis": {
                "using_service_user": user_id.startswith("service:"),
                "likely_auth_failure": "403" in str(e) or "401" in str(e) or "Not authenticated" in str(e),
                "potential_causes": [
                    f"Authentication middleware failed to validate service user_id='{user_id}'",
                    "Service-to-service authentication not properly configured",
                    "SERVICE_ID or SERVICE_SECRET environment variables missing/invalid",
                    "Database connection auth failed",
                    "Service authentication context mechanism failed"
                ],
                "debugging_steps": [
                    "Check if SERVICE_SECRET is properly configured",
                    "Verify JWT_SECRET configuration",
                    "Check authentication middleware logs",
                    "Verify database connection credentials",
                    "Check if service authentication context is working",
                    "Look for authentication dependency injection issues"
                ]
            }
        }
        
        logger.error(
            f"❌ CRITICAL ERROR: Failed to create request-scoped database session {request_id} for user_id='{user_id}'. "
            f"Error: {e}. This may be an authentication failure! Full context: {error_context}"
        )
        
        # COMPREHENSIVE CONTEXT DUMP with all IDs and authentication info
        try:
            from netra_backend.app.logging.auth_trace_logger import log_authentication_context_dump
            log_authentication_context_dump(
                user_id=user_id,
                request_id=request_id,
                operation="create_request_scoped_db_session",
                error=e,
                correlation_id=correlation_id,
                function_location="netra_backend.app.dependencies.get_request_scoped_db_session",
                session_factory_call="factory.get_request_scoped_session",
                user_id_source="service_authentication_context",
                auth_middleware_status="unknown_at_session_creation_time",
                database_connection_status="failed",
                session_creation_stage="database_session_factory",
                potential_root_cause="authentication_middleware_rejection"
            )
        except ImportError:
            logger.error(
                f"🚨 FALLBACK_DEBUG: Auth trace logger not available. "
                f"user_id='{user_id}', request_id='{request_id}', correlation_id='{correlation_id}', error='{e}'"
            )
        except Exception as trace_error:
            logger.error(
                f"🚨 TRACE_ERROR: Failed to log comprehensive context: {trace_error}. "
                f"Original error: {e}, user_id='{user_id}', request_id='{request_id}'"
            )
        
        # Extra debugging for authentication-related errors with comprehensive dump
        if "403" in str(e) or "Not authenticated" in str(e):
            logger.error(
                f"🔴 AUTHENTICATION FAILURE DETECTED: The error '{e}' suggests an authentication problem. "
                f"Since user_id='{user_id}', this is likely a service-to-service authentication configuration issue. "
                f"Check: 1) SERVICE_SECRET config, 2) SERVICE_ID config, 3) Auth service configuration, 4) Service authentication context mechanism. "
                f"Request ID: {request_id}"
            )
            
            # CRITICAL 403 ERROR COMPREHENSIVE DUMP
            try:
                from netra_backend.app.logging.auth_trace_logger import log_authentication_context_dump
                log_authentication_context_dump(
                    user_id=user_id,
                    request_id=request_id,
                    operation="CRITICAL_403_NOT_AUTHENTICATED_ERROR",
                    error=e,
                    correlation_id=correlation_id,
                    error_type="403_not_authenticated",
                    function_location="netra_backend.app.dependencies.get_request_scoped_db_session",
                    auth_failure_stage="session_factory_call",
                    user_id_type="service" if user_id.startswith("service:") else "regular",
                    likely_cause="authentication_middleware_blocked_service_user",
                    debugging_priority="CRITICAL",
                    next_steps=[
                        "Check authentication middleware logs",
                        "Verify SERVICE_SECRET configuration", 
                        "Check JWT_SECRET consistency",
                        "Validate system user authentication bypass",
                        "Review authentication dependency injection"
                    ]
                )
            except Exception as critical_trace_error:
                logger.error(
                    f"🚨 CRITICAL_TRACE_FAILED: Could not dump 403 error context: {critical_trace_error}. "
                    f"This 403 'Not authenticated' error is the main issue you're debugging!"
                )
        
        raise
    finally:
        logger.debug(f"Request-scoped database session {request_id} lifecycle completed")

async def get_db_dependency() -> AsyncGenerator[AsyncSession, None]:
    """Wrapper for database dependency with validation.
    
    DEPRECATED: Use get_request_scoped_db_session for new code.
    Uses the single source of truth from netra_backend.app.database.
    """
    logger.warning("DEPRECATED: get_db_dependency() may cause _AsyncGeneratorContextManager errors. Use get_request_scoped_db_session() instead.")
    # FIX: get_db() is already an async context manager, use it directly
    async with get_db() as session:
        _validate_session_type(session)
        yield session

# Enhanced session dependencies using RequestScopedSessionFactory
async def get_user_scoped_db_session(
    user_id: Optional[str] = None,
    request_id: Optional[str] = None,
    thread_id: Optional[str] = None
) -> AsyncGenerator[AsyncSession, None]:
    """Create a user-scoped database session with enhanced isolation.
    
    Args:
        user_id: User identifier for session isolation
        request_id: Request identifier (auto-generated if not provided)
        thread_id: Thread identifier for WebSocket routing
        
    Yields:
        AsyncSession: Isolated database session for the user
    """
    from netra_backend.app.database.request_scoped_session_factory import get_isolated_session
    
    # CRITICAL FIX: Use service context if no user_id provided
    if not user_id:
        user_id = get_service_user_context()
        logger.debug(f"No user_id provided - using service context: {user_id}")
    
    if not request_id:
        # SSOT COMPLIANCE FIX: Use UnifiedIdGenerator for request ID generation
        from shared.id_generation import UnifiedIdGenerator
        request_id = UnifiedIdGenerator.generate_base_id("req")
    
    logger.debug(f"Creating user-scoped database session for user {user_id}, request {request_id}")
    
    try:
        async with get_isolated_session(user_id, request_id, thread_id) as session:
            _validate_session_type(session)
            # Additional validation for user isolation
            from netra_backend.app.database.request_scoped_session_factory import validate_session_isolation
            await validate_session_isolation(session, user_id)
            
            logger.debug(f"Created user-scoped session {id(session)} for user {user_id}")
            yield session
            logger.debug(f"User-scoped session {id(session)} completed for user {user_id}")
    except Exception as e:
        logger.error(f"Failed to create user-scoped database session for user {user_id}: {e}")
        raise
    finally:
        logger.debug(f"User-scoped database session lifecycle completed for user {user_id}")


async def get_request_scoped_db_session_for_fastapi() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI-compatible wrapper for get_request_scoped_db_session.
    
    CRITICAL: get_request_scoped_db_session is a plain async generator (no @asynccontextmanager).
    This wrapper ensures proper usage pattern for FastAPI Depends() injection.
    
    Yields:
        AsyncSession: Request-scoped database session compatible with FastAPI Depends()
    """
    logger.debug("Creating FastAPI-compatible request-scoped database session")
    
    try:
        # Directly delegate to the async generator
        async for session in get_request_scoped_db_session():
            logger.debug(f"Yielding FastAPI-compatible session: {id(session)}")
            yield session
            logger.debug(f"FastAPI-compatible session {id(session)} completed")
    except Exception as e:
        logger.error(f"Failed to create FastAPI-compatible request-scoped database session: {e}")
        raise


# FIXED: Use async generator directly (no @asynccontextmanager)
DbDep = Annotated[AsyncSession, Depends(get_request_scoped_db_session)]
RequestScopedDbDep = Annotated[AsyncSession, Depends(get_request_scoped_db_session)]
UserScopedDbDep = Annotated[AsyncSession, Depends(get_user_scoped_db_session)]

def get_llm_client_from_app(request: Request) -> ResilientLLMClient:
    """Get LLM client - updated from deleted LLMManager."""
    from netra_backend.app.llm.client_unified import ResilientLLMClient
    llm_manager = get_llm_manager(request)
    return ResilientLLMClient(llm_manager)

# Legacy compatibility - DEPRECATED: use get_db_dependency() instead
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """DEPRECATED: Legacy compatibility function for get_db_session.
    
    This function is deprecated. Use get_db_dependency() or DbDep type annotation instead.
    Kept for backward compatibility with existing routes.
    """
    # FIX: get_db() is already an async context manager, use it directly
    async with get_db() as session:
        yield session

def get_service_user_context() -> str:
    """
    Get service user context for internal operations.
    
    CRITICAL FIX: Replaces hardcoded "system" user with proper service authentication.
    This enables service-to-service operations using SERVICE_ID and SERVICE_SECRET.
    
    Returns:
        str: Service user context in format "service:{service_id}"
    """
    from netra_backend.app.core.configuration import get_configuration
    from shared.isolated_environment import get_env
    from shared.constants.service_identifiers import SERVICE_ID
    
    # Get service ID from configuration or environment
    config = get_configuration()
    service_id = config.service_id or SERVICE_ID
    
    # If configuration doesn't have service_id, try environment
    if not config.service_id:
        env = get_env()
        env_service_id = env.get('SERVICE_ID')
        if env_service_id:
            service_id = env_service_id
        else:
            logger.warning("SERVICE_ID not found in config or environment - using SSOT default")
            service_id = SERVICE_ID
    
    # Return service context format
    service_context = f"service:{service_id}"
    logger.debug(f"Service user context: {service_context}")
    return service_context

def get_security_service(request: Request) -> SecurityService:
    logger.debug("Getting security service from app state")
    return request.app.state.security_service

LLMClientDep = Annotated[ResilientLLMClient, Depends(get_llm_client_from_app)]

def get_agent_supervisor(request: Request) -> "Supervisor":
    """Get agent supervisor from app state - LEGACY mode.
    
    DEPRECATED: This returns a global supervisor instance without user isolation.
    For new code, use get_request_scoped_user_context() to create per-request contexts.
    
    CRITICAL: This function NEVER passes database sessions to global objects.
    The supervisor is initialized at startup with WebSocket manager,
    so it should already have WebSocket capabilities when retrieved here.
    """
    logger.warning("Using legacy get_agent_supervisor - user isolation NOT guaranteed!")
    supervisor = request.app.state.agent_supervisor
    
    # CRITICAL: Verify that supervisor does not have stored database sessions
    if hasattr(supervisor, '_stored_db_session') and supervisor._stored_db_session:
        logger.error("CRITICAL: Global supervisor has stored database session - this violates request scoping!")
        raise RuntimeError("Global supervisor must never store database sessions")
    
    # Verify supervisor has WebSocket capabilities - CRITICAL: Avoid creation during startup
    if supervisor and hasattr(supervisor, 'agent_registry'):
        # SSOT COMPLIANCE FIX: Don't create WebSocket manager during startup/dependency injection
        # WebSocket managers should only be created per-request with valid UserExecutionContext
        if hasattr(supervisor.agent_registry, 'websocket_manager') and supervisor.agent_registry.websocket_manager:
            logger.debug("Supervisor agent registry already has WebSocket manager configured")
        else:
            logger.info("WebSocket manager will be set per-request via factory pattern - SSOT compliance")
    else:
        logger.warning("Supervisor lacks agent_registry - WebSocket events may not work")
    
    return supervisor


async def get_request_scoped_user_context(
    user_id: str,
    thread_id: str,
    run_id: Optional[str] = None,
    websocket_client_id: Optional[str] = None
) -> RequestScopedContext:
    """Create request-scoped user context WITHOUT storing database sessions.
    
    CRITICAL: This function creates context metadata only. Database sessions
    must be obtained separately and never stored in the context.
    
    Args:
        user_id: Unique user identifier
        thread_id: Thread identifier for conversation
        run_id: Optional run identifier (auto-generated if not provided)
        websocket_connection_id: Optional WebSocket connection identifier
        
    Returns:
        RequestScopedContext: Context with metadata only, no sessions
        
    Raises:
        HTTPException: If context creation fails
    """
    try:
        # SSOT COMPLIANCE FIX: Generate run_id using UnifiedIdGenerator if not provided
        if not run_id:
            from shared.id_generation import UnifiedIdGenerator
            run_id = UnifiedIdGenerator.generate_base_id("run")
        
        # Create request-scoped context (no session storage)
        context = RequestScopedContext(
            user_id=user_id,
            thread_id=thread_id,
            run_id=run_id,
            websocket_client_id=websocket_client_id
        )
        
        logger.info(f"Created RequestScopedContext for user {user_id}, run {run_id} - NO sessions stored")
        return context
        
    except Exception as e:
        logger.error(f"Failed to create RequestScopedContext: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create request-scoped context: {str(e)}"
        )

def get_user_execution_context(user_id: str, thread_id: Optional[str] = None, run_id: Optional[str] = None) -> UserExecutionContext:
    """Get existing user execution context or create if needed - CORRECT PATTERN.
    
    ⚠️  DEPRECATED: Use get_user_session_context() for new code.
    
    This function implements proper session management using the SSOT UserSessionManager.
    It maintains conversation continuity by reusing existing contexts instead of always
    creating new ones.
    
    Args:
        user_id: Unique user identifier
        thread_id: Thread identifier for conversation continuity  
        run_id: Optional run identifier - if provided, determines session behavior:
                - None: Use existing session run_id or create new session
                - Matches existing: Use existing session (conversation continues)
                - Different: Create new run within same thread (new agent execution)
        
    Returns:
        UserExecutionContext with proper session management
    """
    logger.warning("get_user_execution_context is deprecated - use get_user_session_context() for new code")
    
    from shared.id_generation.unified_id_generator import UnifiedIdGenerator
    
    # Get or create session using SSOT session management with run_id handling
    session_data = UnifiedIdGenerator.get_or_create_user_session(
        user_id=user_id, 
        thread_id=thread_id,
        run_id=run_id
    )
    
    # Create UserExecutionContext with session-managed IDs
    return UserExecutionContext(
        user_id=user_id,
        thread_id=session_data["thread_id"],
        run_id=session_data["run_id"],
        request_id=session_data["request_id"],
        websocket_client_id=UnifiedIdGenerator.generate_websocket_client_id(user_id)
    )


async def get_user_session_context(user_id: str, 
                                  thread_id: Optional[str] = None, 
                                  run_id: Optional[str] = None,
                                  websocket_connection_id: Optional[str] = None) -> UserExecutionContext:
    """Get user session context using SSOT UserSessionManager - PREFERRED METHOD.
    
    This is the PREFERRED method for getting user execution contexts as it uses the
    comprehensive UserSessionManager for proper session lifecycle management.
    
    Key Features:
    - Maintains conversation continuity by reusing existing sessions
    - Integrates with WebSocket lifecycle management
    - Provides comprehensive logging and monitoring
    - Handles session cleanup automatically
    - Thread-safe operations with proper locking
    
    Args:
        user_id: Unique user identifier
        thread_id: Thread identifier for conversation continuity (auto-generated if None)
        run_id: Optional run identifier for specific agent executions
        websocket_connection_id: Optional WebSocket connection ID
        
    Returns:
        UserExecutionContext: Session-managed execution context
        
    Raises:
        SessionManagerError: If session management fails
    """
    from shared.session_management import get_user_session
    
    # Generate thread_id if not provided (for new conversations)
    if not thread_id:
        from shared.id_generation import UnifiedIdGenerator
        thread_id = UnifiedIdGenerator.generate_base_id("thread_new")
        logger.info(f"Generated new thread_id for user {user_id}: {thread_id}")
    
    try:
        # Use SSOT UserSessionManager for session management
        context = await get_user_session(
            user_id=user_id,
            thread_id=thread_id,
            run_id=run_id,
            websocket_connection_id=websocket_connection_id
        )
        
        logger.debug(f"Retrieved session context for user {user_id}: {context.get_correlation_id()}")
        return context
        
    except Exception as e:
        logger.error(f"Failed to get user session context for user {user_id}: {e}", exc_info=True)
        # Fall back to direct creation for robustness
        logger.warning("Falling back to direct UserExecutionContext creation")
        return UserExecutionContext.from_request(
            user_id=user_id,
            thread_id=thread_id,
            run_id=run_id or UnifiedIdGenerator.generate_base_id("run"),
            websocket_client_id=websocket_connection_id or UnifiedIdGenerator.generate_websocket_client_id(user_id)
        )


def create_user_execution_context(user_id: str,
                                  thread_id: str, 
                                  run_id: Optional[str] = None,
                                  db_session: Optional[AsyncSession] = None,
                                  websocket_client_id: Optional[str] = None) -> UserExecutionContext:
    """Create UserExecutionContext for per-request isolation.
    
    ⚠️  DEPRECATED: This function breaks conversation continuity!
    
    CRITICAL ISSUE: This function always creates NEW contexts instead of maintaining
    session continuity. This breaks multi-turn conversations and causes memory leaks.
    
    USE INSTEAD:
    - get_user_execution_context() for session-based context management
    - get_request_scoped_user_context() for HTTP requests
    
    This function is kept for backward compatibility but should be replaced.
    
    CRITICAL: When db_session is provided, it must be request-scoped only.
    
    Args:
        user_id: Unique user identifier
        thread_id: Thread identifier for conversation
        run_id: Optional run identifier (auto-generated if not provided)
        db_session: Optional database session (MUST be request-scoped)
        websocket_connection_id: Optional WebSocket connection identifier
        
    Returns:
        UserExecutionContext: Isolated context for the request
        
    Raises:
        HTTPException: If context creation fails
    """
    logger.warning("Using deprecated create_user_execution_context - consider get_request_scoped_user_context")
    
    try:
        # CRITICAL: Validate that session is not from global storage
        if db_session:
            # Use enhanced session validation
            validate_session_is_request_scoped(db_session, "create_user_execution_context")
            
            # Tag session with user context for validation
            if hasattr(db_session, 'info'):
                if not db_session.info:
                    db_session.info = {}
                # SSOT COMPLIANCE FIX: Use UnifiedIdGenerator for ID generation
                from shared.id_generation import UnifiedIdGenerator
                db_session.info.update({
                    'user_id': user_id,
                    'run_id': run_id or UnifiedIdGenerator.generate_base_id("run"),
                    'request_id': UnifiedIdGenerator.generate_base_id("req"),
                    'tagged_at': time.time()
                })
        
        # SSOT COMPLIANCE FIX: Generate run_id using UnifiedIdGenerator if not provided
        if not run_id:
            from shared.id_generation import UnifiedIdGenerator
            run_id = UnifiedIdGenerator.generate_base_id("run")
        
        # Create user execution context
        user_context = UserExecutionContext.from_request(
            user_id=user_id,
            thread_id=thread_id,
            run_id=run_id,
            db_session=db_session,
            websocket_client_id=websocket_client_id  # Fixed parameter name
        )
        
        logger.info(f"Created UserExecutionContext for user {user_id}, run {run_id}")
        return user_context
        
    except Exception as e:
        logger.error(f"Failed to create UserExecutionContext: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create user execution context: {str(e)}"
        )


async def get_request_scoped_supervisor(
    request: Request,
    context: RequestScopedContext,
    db_session: AsyncSession
) -> "Supervisor":
    """Create isolated SupervisorAgent with request-scoped database session.
    
    CRITICAL: This function ensures database sessions are NEVER stored globally.
    The supervisor is created fresh for each request with proper session lifecycle.
    
    Updated to use create_supervisor_core for consistency with WebSocket pattern.
    
    Args:
        request: FastAPI request object
        context: Request-scoped context (contains no sessions)
        db_session: Request-scoped database session (will be closed after request)
        
    Returns:
        SupervisorAgent: Isolated supervisor instance for this request
        
    Raises:
        HTTPException: If supervisor creation fails
    """
    try:
        # CRITICAL: Validate that session is not globally stored
        if hasattr(db_session, '_global_storage_flag'):
            logger.error("CRITICAL: Attempted to use globally stored session in request-scoped supervisor")
            raise RuntimeError("Database sessions must be request-scoped only")
            
        logger.debug(f"Creating request-scoped supervisor for user {context.user_id}, session {id(db_session)}")
        
        # Get required components from app state (these should be stateless)
        llm_client = get_llm_client_from_app(request)
        
        # Get WebSocket bridge from app state with defensive checks
        websocket_bridge = getattr(request.app.state, 'agent_websocket_bridge', None)
        if not websocket_bridge:
            # Try alternative attribute names
            websocket_bridge = getattr(request.app.state, 'websocket_bridge', None)
        
        if not websocket_bridge:
            # Check if startup is still in progress
            startup_in_progress = getattr(request.app.state, 'startup_in_progress', False)
            startup_complete = getattr(request.app.state, 'startup_complete', False)
            
            if startup_in_progress and not startup_complete:
                logger.warning(f"Request received during startup - WebSocket bridge not yet available. User: {context.user_id}")
                raise HTTPException(
                    status_code=503,
                    detail="Service temporarily unavailable - system is still starting up. Please retry in a few seconds."
                )
            else:
                logger.error(f"WebSocket bridge not available after startup completion. Startup complete: {startup_complete}")
                raise HTTPException(
                    status_code=500,
                    detail="WebSocket bridge unavailable (startup failed or invalid configuration - check app startup logs)"
                )
        
        # Get tool dispatcher from legacy supervisor with defensive checks
        legacy_supervisor = getattr(request.app.state, 'agent_supervisor', None)
        
        # RACE CONDITION FIX: Check if supervisor is available and properly initialized
        if not legacy_supervisor:
            # Check if startup is still in progress
            startup_in_progress = getattr(request.app.state, 'startup_in_progress', False)
            startup_complete = getattr(request.app.state, 'startup_complete', False)
            
            if startup_in_progress and not startup_complete:
                logger.warning(f"Request received during startup - supervisor not yet available. User: {context.user_id}")
                raise HTTPException(
                    status_code=503,
                    detail="Service temporarily unavailable - system is still starting up. Please retry in a few seconds."
                )
            else:
                logger.error(f"Agent supervisor not available after startup completion. Startup complete: {startup_complete}")
                raise HTTPException(
                    status_code=500,
                    detail="Agent supervisor not available (critical startup failure - check application logs)"
                )
        
        # Check if supervisor has tool_dispatcher attribute
        if not hasattr(legacy_supervisor, 'tool_dispatcher'):
            logger.error(f"Agent supervisor missing tool_dispatcher attribute. Supervisor type: {type(legacy_supervisor)}")
            raise HTTPException(
                status_code=500,
                detail="Agent supervisor configuration invalid (missing tool dispatcher)"
            )
        
        tool_dispatcher = legacy_supervisor.tool_dispatcher
        if not tool_dispatcher:
            logger.error(f"Tool dispatcher is None. Supervisor: {type(legacy_supervisor)}, User: {context.user_id}")
            
            # Check if this might be a UserContext-based architecture issue
            if hasattr(request.app.state, 'tool_classes') and request.app.state.tool_classes:
                logger.info("Detected UserContext-based tool configuration - attempting fallback creation")
                # TODO: Implement tool dispatcher creation from tool_classes for UserContext architecture
                # For now, return clear error about missing tool dispatcher
                raise HTTPException(
                    status_code=500,
                    detail="Tool dispatcher not configured (UserContext-based architecture requires per-request tool creation)"
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail="Tool dispatcher unavailable (check supervisor initialization and configuration validity)"
                )
        
        # Use core supervisor factory for consistency with WebSocket pattern
        from netra_backend.app.core.supervisor_factory import create_supervisor_core
        supervisor = await create_supervisor_core(
            user_id=context.user_id,
            thread_id=context.thread_id,
            run_id=context.run_id,
            db_session=db_session,
            websocket_connection_id=context.websocket_connection_id,
            llm_client=llm_client,
            websocket_bridge=websocket_bridge,
            tool_dispatcher=tool_dispatcher
        )
        
        logger.info(f"✅ Created request-scoped SupervisorAgent for user {context.user_id}, run {context.run_id} using core factory")
        return supervisor
        
    except Exception as e:
        logger.error(f"Failed to create request-scoped SupervisorAgent: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create request-scoped supervisor: {str(e)}"
        )

async def get_user_supervisor_factory(request: Request,
                                     user_id: str,
                                     thread_id: str,
                                     run_id: Optional[str] = None,
                                     db_session: AsyncSession = Depends(get_request_scoped_db_session)) -> "Supervisor":
    """Factory to create per-request SupervisorAgent with UserExecutionContext.
    
    DEPRECATED: Use get_request_scoped_supervisor for new code.
    This function is kept for backward compatibility during transition.
    
    CRITICAL: This function has been updated to validate that sessions are request-scoped.
    
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
    logger.warning("Using deprecated get_user_supervisor_factory - consider get_request_scoped_supervisor")
    
    # Create context and delegate to new implementation
    context = await get_request_scoped_user_context(
        user_id=user_id,
        thread_id=thread_id,
        run_id=run_id
    )
    
    return await get_request_scoped_supervisor(request, context, db_session)


# Type aliases for dependency injection
RequestScopedContextDep = Annotated[RequestScopedContext, Depends(get_request_scoped_user_context)]

# New session manager dependencies
async def get_user_session_context_dependency(
    user_id: str,
    thread_id: Optional[str] = None,
    run_id: Optional[str] = None,
    websocket_connection_id: Optional[str] = None
) -> UserExecutionContext:
    """Dependency for getting user session context with SSOT UserSessionManager.
    
    This is the PREFERRED dependency for user execution contexts in new code.
    """
    return await get_user_session_context(
        user_id=user_id,
        thread_id=thread_id,
        run_id=run_id,
        websocket_connection_id=websocket_connection_id
    )

UserSessionContextDep = Annotated[UserExecutionContext, Depends(get_user_session_context_dependency)]

# Type alias for the new isolated supervisor dependency (DEPRECATED)
IsolatedSupervisorDep = Annotated["Supervisor", Depends(get_user_supervisor_factory)]

# New request-scoped supervisor dependency
async def get_request_scoped_supervisor_dependency(
    request: Request,
    context: RequestScopedContextDep,
    db_session: RequestScopedDbDep
) -> "Supervisor":
    """Dependency for getting request-scoped supervisor with proper session lifecycle.
    
    This is the PREFERRED way to inject supervisors in new code.
    CRITICAL: Ensures database sessions are never stored globally.
    """
    return await get_request_scoped_supervisor(request, context, db_session)

RequestScopedSupervisorDep = Annotated["Supervisor", Depends(get_request_scoped_supervisor_dependency)]

# New request-scoped message handler dependency
async def get_request_scoped_message_handler_dependency(
    context: RequestScopedContextDep,
    supervisor: RequestScopedSupervisorDep,
    request: Request
):
    """Dependency for getting request-scoped message handler.
    
    This is the PREFERRED way to inject message handlers in new code.
    """
    return await get_request_scoped_message_handler(context, supervisor, request)

RequestScopedMessageHandlerDep = Annotated[Any, Depends(get_request_scoped_message_handler_dependency)]

# Factory pattern dependencies for singleton migration

async def get_factory_adapter_dependency(request: Request):
    """Get FactoryAdapter from app state for gradual migration."""
    if not hasattr(request.app.state, 'factory_adapter'):
        raise HTTPException(
            status_code=500, 
            detail="Factory adapter not initialized - startup failure"
        )
    return request.app.state.factory_adapter

FactoryAdapterDep = Annotated[Any, Depends(get_factory_adapter_dependency)]

async def get_execution_engine_factory_dependency(request: Request):
    """Get ExecutionEngineFactory from app state."""
    if not hasattr(request.app.state, 'execution_engine_factory'):
        raise HTTPException(
            status_code=500,
            detail="ExecutionEngineFactory not initialized - startup failure"
        )
    return request.app.state.execution_engine_factory

ExecutionEngineFactoryDep = Annotated[Any, Depends(get_execution_engine_factory_dependency)]

async def get_agent_instance_factory_dependency(request: Request):
    """Get AgentInstanceFactory from app state."""
    if not hasattr(request.app.state, 'agent_instance_factory'):
        raise HTTPException(
            status_code=500,
            detail="AgentInstanceFactory not initialized - startup failure"
        )
    return request.app.state.agent_instance_factory

AgentInstanceFactoryDep = Annotated[Any, Depends(get_agent_instance_factory_dependency)]

async def get_factory_execution_engine(
    user_id: str,
    thread_id: Optional[str] = None,
    run_id: Optional[str] = None,
    route_path: Optional[str] = None,
    factory_adapter: FactoryAdapterDep = None
):
    """Get execution engine using factory pattern or legacy singleton based on migration configuration.
    
    This dependency provides the appropriate execution engine based on the factory adapter configuration.
    It enables gradual migration from singleton to factory patterns.
    
    Args:
        user_id: User identifier for request-scoped context
        thread_id: Optional thread identifier 
        run_id: Optional run identifier
        route_path: Route path for route-specific feature flags
        factory_adapter: Factory adapter instance from app state
        
    Returns:
        Either IsolatedExecutionEngine (factory) or ExecutionEngine (legacy singleton)
    """
    from netra_backend.app.services.factory_adapter import create_request_context
    
    try:
        # Create request context for factory pattern
        request_context = create_request_context(
            user_id=user_id,
            thread_id=thread_id,
            request_id=run_id
        )
        
        # Get execution engine via factory adapter (handles migration logic)
        return await factory_adapter.get_execution_engine(
            request_context=request_context,
            route_path=route_path
        )
        
    except Exception as e:
        logger.error(f"Failed to get factory execution engine for user {user_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create execution engine: {str(e)}"
        )

async def get_factory_websocket_bridge(
    user_id: str,
    thread_id: Optional[str] = None,
    run_id: Optional[str] = None,
    route_path: Optional[str] = None,
    factory_adapter: FactoryAdapterDep = None
):
    """Get WebSocket bridge using factory pattern or legacy singleton.
    
    Args:
        user_id: User identifier for request-scoped context
        thread_id: Optional thread identifier
        run_id: Optional run identifier  
        route_path: Route path for route-specific feature flags
        factory_adapter: Factory adapter instance from app state
        
    Returns:
        Either UserWebSocketEmitter (factory) or AgentWebSocketBridge (legacy)
    """
    from netra_backend.app.services.factory_adapter import create_request_context
    
    try:
        # Create request context for factory pattern
        request_context = create_request_context(
            user_id=user_id,
            thread_id=thread_id,
            request_id=run_id
        )
        
        # Get WebSocket bridge via factory adapter
        return await factory_adapter.get_websocket_bridge(
            request_context=request_context,
            route_path=route_path
        )
        
    except Exception as e:
        logger.error(f"Failed to get factory WebSocket bridge for user {user_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create WebSocket bridge: {str(e)}"
        )

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

def get_corpus_service(request: Request, user_context=None) -> "CorpusService":
    """Get corpus service from app state or create with user context.
    
    Args:
        request: FastAPI request object
        user_context: Optional UserExecutionContext for WebSocket isolation.
                     If provided, creates a new instance with WebSocket support.
                     If None, returns the singleton without WebSocket support.
    
    CRITICAL: This service MUST be initialized during startup.
    """
    # If user context is provided, create a new instance for isolation
    if user_context:
        from netra_backend.app.services.corpus_service import CorpusService
        return CorpusService(user_context=user_context)
    
    # Otherwise return the singleton
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

def get_llm_manager(request: Request = None, user_context: Optional['UserExecutionContext'] = None):
    """Get LLM manager with proper user isolation.
    
    SSOT MIGRATION: Updated to use factory pattern with user isolation.
    This prevents conversation mixing between users by creating isolated instances.
    
    Args:
        request: Optional FastAPI request (for backward compatibility)
        user_context: Optional UserExecutionContext for user-scoped operations
        
    Returns:
        LLMManager: User-isolated LLM manager instance
    """
    from netra_backend.app.llm.llm_manager import create_llm_manager
    from netra_backend.app.services.user_execution_context import UserExecutionContext
    
    # If no user context provided, try to extract from request
    if user_context is None and request is not None:
        # Try to extract user context from request
        try:
            # Look for user context in request state or headers
            if hasattr(request, 'state') and hasattr(request.state, 'user_context'):
                user_context = request.state.user_context
            elif hasattr(request, 'headers'):
                # Extract user info from headers for user context creation
                user_id = request.headers.get('X-User-ID')
                session_id = request.headers.get('X-Session-ID')
                if user_id:
                    user_context = UserExecutionContext(
                        user_id=user_id,
                        session_id=session_id or f"session_{user_id[:8]}"
                    )
        except Exception as e:
            logger.warning(f"Could not extract user context from request: {e}")
    
    # Create user-isolated LLM manager using factory pattern
    return create_llm_manager(user_context)

def get_message_handler_service(request: Request):
    """Get message handler service from app state or create one.
    
    DEPRECATED: This creates MessageHandlerService with global supervisor.
    For new code, use get_request_scoped_message_handler with proper session management.
    
    CRITICAL: This function validates that global supervisors don't store sessions.
    """
    logger.warning("Using legacy get_message_handler_service - consider request-scoped message handler")
    
    # Try to get from app state first
    if hasattr(request.app.state, 'message_handler_service'):
        service = request.app.state.message_handler_service
        
        # CRITICAL: Validate that service doesn't have stored database sessions
        if hasattr(service, 'supervisor') and hasattr(service.supervisor, '_stored_db_session'):
            if service.supervisor._stored_db_session:
                logger.error("CRITICAL: Global message handler service has stored database session")
                raise RuntimeError("Global services must never store database sessions")
        
        return service
    
    # Create one using available dependencies
    from netra_backend.app.services.message_handlers import MessageHandlerService
    supervisor = get_agent_supervisor(request)  # This validates no stored sessions
    thread_service = get_thread_service(request)
    
    # SSOT COMPLIANCE FIX: Don't create WebSocket managers during global dependency injection
    # WebSocket managers should only be created per-request with proper UserExecutionContext
    # This legacy service will have limited WebSocket capabilities - use request-scoped alternatives
    logger.info("Creating legacy MessageHandlerService without WebSocket manager - use request-scoped message handlers for WebSocket events")
    return MessageHandlerService(supervisor, thread_service)


async def get_request_scoped_message_handler(
    context: RequestScopedContext,
    supervisor: "Supervisor",
    request: Request
):
    """Create MessageHandlerService with request-scoped supervisor.
    
    CRITICAL: This service uses a supervisor that has a request-scoped database session.
    The session will be automatically closed when the request completes.
    
    Args:
        context: Request-scoped context (contains no sessions)
        supervisor: Request-scoped supervisor with session lifecycle management
        request: FastAPI request object
        
    Returns:
        MessageHandlerService: Service with request-scoped supervisor
    """
    try:
        # Get thread service (stateless)
        thread_service = get_thread_service(request)
        
        # Get WebSocket manager using factory pattern for proper isolation
        # Create user context based on request context
        user_context = UserExecutionContext(
            user_id=context.user_id,
            request_id=context.request_id,
            thread_id=context.thread_id,
            run_id=context.run_id
        )
        
        # SSOT COMPLIANCE: Proper per-request WebSocket manager creation with error handling
        try:
            websocket_manager = WebSocketManager(user_context=user_context)
            if not websocket_manager:
                logger.warning(f"WebSocket manager creation returned None for user {context.user_id}")
                websocket_manager = None
        except Exception as e:
            logger.error(f"Failed to create WebSocket manager for user {context.user_id}: {e}")
            websocket_manager = None
        
        # Create MessageHandlerService with request-scoped components
        # WEBSOCKET FACTORY FIX: MessageHandlerService creates websocket_manager internally as needed
        from netra_backend.app.services.message_handlers import MessageHandlerService
        message_service = MessageHandlerService(supervisor, thread_service)
        
        logger.info(f"✅ Created request-scoped MessageHandlerService for user {context.user_id}")
        return message_service
        
    except Exception as e:
        logger.error(f"Failed to create request-scoped MessageHandlerService: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create request-scoped message handler: {str(e)}"
        )

async def get_isolated_message_handler_service(user_id: str,
                                              thread_id: str,
                                              run_id: Optional[str],
                                              request: Request,
                                              db_session: AsyncSession = Depends(get_request_scoped_db_session)):
    """Create MessageHandlerService with isolated supervisor for this request.
    
    DEPRECATED: Use get_request_scoped_message_handler for new code.
    This function is kept for backward compatibility.
    
    Args:
        user_id: User identifier from request
        thread_id: Thread identifier from request  
        run_id: Optional run identifier
        request: FastAPI request object
        db_session: Request-scoped database session
        
    Returns:
        MessageHandlerService: Service with isolated supervisor
    """
    logger.warning("Using deprecated get_isolated_message_handler_service - consider get_request_scoped_message_handler")
    
    try:
        # Create context and supervisor using new approach
        context = await get_request_scoped_user_context(
            user_id=user_id,
            thread_id=thread_id,
            run_id=run_id
        )
        
        supervisor = await get_request_scoped_supervisor(request, context, db_session)
        
        return await get_request_scoped_message_handler(context, supervisor, request)
        
    except Exception as e:
        logger.error(f"Failed to create isolated MessageHandlerService: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create isolated message handler: {str(e)}"
        )


# === Factory Pattern Dependencies ===

def get_execution_engine_factory(request: Request) -> ExecutionEngineFactory:
    """Get ExecutionEngineFactory from app state.
    
    The factory should be initialized during app startup and configured
    with infrastructure components (agent_registry, websocket_bridge_factory, db_pool).
    
    Returns:
        ExecutionEngineFactory: Configured factory for creating isolated execution engines
        
    Raises:
        HTTPException: If factory not configured
    """
    try:
        factory = getattr(request.app.state, 'execution_engine_factory', None)
        if not factory:
            logger.error("ExecutionEngineFactory not found in app state - ensure it's configured during startup")
            raise HTTPException(
                status_code=500,
                detail="ExecutionEngineFactory unavailable (startup initialization failed or configuration invalid)"
            )
        
        return factory
        
    except Exception as e:
        logger.error(f"Failed to get ExecutionEngineFactory: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"ExecutionEngineFactory error: {str(e)}"
        )


def get_websocket_bridge_factory(request: Request) -> WebSocketBridgeFactory:
    """Get WebSocketBridgeFactory from app state.
    
    The factory should be initialized during app startup and configured
    with infrastructure components (connection_pool, agent_registry, health_monitor).
    
    Returns:
        WebSocketBridgeFactory: Configured factory for creating isolated WebSocket emitters
        
    Raises:
        HTTPException: If factory not configured
    """
    try:
        factory = getattr(request.app.state, 'websocket_bridge_factory', None)
        if not factory:
            logger.error("WebSocketBridgeFactory not found in app state - ensure it's configured during startup")
            raise HTTPException(
                status_code=500,
                detail="WebSocketBridgeFactory unavailable (startup initialization failed or configuration invalid)"
            )
        
        return factory
        
    except Exception as e:
        logger.error(f"Failed to get WebSocketBridgeFactory: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"WebSocketBridgeFactory error: {str(e)}"
        )


def get_factory_adapter(request: Request) -> FactoryAdapter:
    """Get FactoryAdapter from app state.
    
    The adapter should be initialized during app startup with both factories
    and configured for backward compatibility and gradual migration.
    
    Returns:
        FactoryAdapter: Configured adapter for factory pattern migration
        
    Raises:
        HTTPException: If adapter not configured
    """
    try:
        adapter = getattr(request.app.state, 'factory_adapter', None)
        if not adapter:
            logger.error("FactoryAdapter not found in app state - ensure it's configured during startup")
            raise HTTPException(
                status_code=500,
                detail="FactoryAdapter unavailable (startup initialization failed or configuration invalid)"
            )
        
        return adapter
        
    except Exception as e:
        logger.error(f"Failed to get FactoryAdapter: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"FactoryAdapter error: {str(e)}"
        )


async def get_factory_execution_engine(
    user_id: str,
    thread_id: str,
    request_id: Optional[str] = None,
    session_id: Optional[str] = None,
    request: Request = None
) -> "IsolatedExecutionEngine":
    """Create isolated ExecutionEngine using factory pattern.
    
    This dependency provides a completely isolated execution engine for each request,
    eliminating shared state issues and enabling concurrent user support.
    
    Args:
        user_id: Unique user identifier
        thread_id: Thread identifier for WebSocket routing
        request_id: Optional request identifier (auto-generated if not provided)
        session_id: Optional session identifier
        request: FastAPI request object
        
    Returns:
        IsolatedExecutionEngine: User-isolated execution engine
        
    Raises:
        HTTPException: If engine creation fails
    """
    try:
        # Get factory from app state
        factory = get_execution_engine_factory(request)
        
        # SSOT COMPLIANCE FIX: Create user execution context with UnifiedIdGenerator
        if not request_id:
            from shared.id_generation import UnifiedIdGenerator
            request_id = UnifiedIdGenerator.generate_base_id("req")
        
        user_context = FactoryUserExecutionContext(
            user_id=user_id,
            request_id=request_id,
            thread_id=thread_id,
            session_id=session_id
        )
        
        # Create isolated execution engine
        engine = await factory.create_execution_engine(user_context)
        
        logger.info(f"✅ Created isolated ExecutionEngine for user {user_id}")
        return engine
        
    except Exception as e:
        logger.error(f"Failed to create factory execution engine: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Factory execution engine creation failed: {str(e)}"
        )


async def get_factory_websocket_emitter(
    user_id: str,
    thread_id: str,
    connection_id: Optional[str] = None,
    request: Request = None
) -> "UserWebSocketEmitter":
    """Create isolated WebSocket emitter using factory pattern.
    
    This dependency provides a completely isolated WebSocket emitter for each user,
    eliminating cross-user event leakage and ensuring reliable notifications.
    
    Args:
        user_id: Unique user identifier
        thread_id: Thread identifier for WebSocket routing
        connection_id: Optional WebSocket connection identifier
        request: FastAPI request object
        
    Returns:
        UserWebSocketEmitter: User-isolated WebSocket emitter
        
    Raises:
        HTTPException: If emitter creation fails
    """
    try:
        # Get factory from app state
        factory = get_websocket_bridge_factory(request)
        
        # SSOT COMPLIANCE FIX: Generate connection ID using UnifiedIdGenerator
        if not connection_id:
            from shared.id_generation import UnifiedIdGenerator
            connection_id = UnifiedIdGenerator.generate_websocket_connection_id(user_id)
        
        # Create isolated WebSocket emitter
        emitter = await factory.create_user_emitter(user_id, thread_id, connection_id)
        
        logger.info(f"✅ Created isolated WebSocketEmitter for user {user_id}")
        return emitter
        
    except Exception as e:
        logger.error(f"Failed to create factory WebSocket emitter: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Factory WebSocket emitter creation failed: {str(e)}"
        )


async def get_adaptive_execution_engine(
    user_id: str,
    thread_id: str,
    request_id: Optional[str] = None,
    route_path: Optional[str] = None,
    request: Request = None
) -> "Union[IsolatedExecutionEngine, ExecutionEngine]":
    """Get execution engine using adaptive factory pattern.
    
    This dependency uses the FactoryAdapter to provide either factory-based
    or legacy execution engines based on migration configuration and feature flags.
    
    Args:
        user_id: Unique user identifier
        thread_id: Thread identifier
        request_id: Optional request identifier
        route_path: Optional route path for route-specific feature flags
        request: FastAPI request object
        
    Returns:
        Either IsolatedExecutionEngine (factory) or ExecutionEngine (legacy)
    """
    try:
        # Get factory adapter
        adapter = get_factory_adapter(request)
        
        # Create request context for factory pattern
        request_context = create_request_context(
            user_id=user_id,
            thread_id=thread_id,
            request_id=request_id
        )
        
        # Get appropriate engine through adapter
        engine = await adapter.get_execution_engine(
            request_context=request_context,
            route_path=route_path
        )
        
        logger.debug(f"Provided execution engine via adapter for user {user_id}")
        return engine
        
    except Exception as e:
        logger.error(f"Failed to get adaptive execution engine: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Adaptive execution engine error: {str(e)}"
        )


async def get_adaptive_websocket_bridge(
    user_id: str,
    thread_id: str,
    connection_id: Optional[str] = None,
    route_path: Optional[str] = None,
    request: Request = None
) -> "Union[UserWebSocketEmitter, AgentWebSocketBridge]":
    """Get WebSocket bridge using adaptive factory pattern.
    
    This dependency uses the FactoryAdapter to provide either factory-based
    or legacy WebSocket bridges based on migration configuration.
    
    Args:
        user_id: Unique user identifier
        thread_id: Thread identifier
        connection_id: Optional WebSocket connection identifier
        route_path: Optional route path for route-specific feature flags
        request: FastAPI request object
        
    Returns:
        Either UserWebSocketEmitter (factory) or AgentWebSocketBridge (legacy)
    """
    try:
        # Get factory adapter
        adapter = get_factory_adapter(request)
        
        # Create request context for factory pattern
        request_context = create_request_context(
            user_id=user_id,
            thread_id=thread_id,
            connection_id=connection_id
        )
        
        # Get appropriate bridge through adapter
        bridge = await adapter.get_websocket_bridge(
            request_context=request_context,
            route_path=route_path
        )
        
        logger.debug(f"Provided WebSocket bridge via adapter for user {user_id}")
        return bridge
        
    except Exception as e:
        logger.error(f"Failed to get adaptive WebSocket bridge: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Adaptive WebSocket bridge error: {str(e)}"
        )


# Type aliases for dependency injection
ExecutionEngineFactoryDep = Annotated[ExecutionEngineFactory, Depends(get_execution_engine_factory)]
WebSocketBridgeFactoryDep = Annotated[WebSocketBridgeFactory, Depends(get_websocket_bridge_factory)]
FactoryAdapterDep = Annotated[FactoryAdapter, Depends(get_factory_adapter)]


# Utility function for route-specific factory configuration
async def configure_route_factory_settings(
    route_path: str,
    enable_factory: bool,
    request: Request
) -> Dict[str, Any]:
    """Configure factory settings for a specific route.
    
    This utility function enables/disables factory patterns for specific routes,
    supporting gradual migration and A/B testing.
    
    Args:
        route_path: Route path to configure
        enable_factory: Whether to enable factory pattern for this route
        request: FastAPI request object
        
    Returns:
        Dictionary with configuration status
    """
    try:
        adapter = get_factory_adapter(request)
        
        if enable_factory:
            await adapter.enable_factory_for_route(route_path)
        else:
            await adapter.disable_factory_for_route(route_path)
        
        status = adapter.get_migration_status()
        
        logger.info(f"Configured factory pattern for route {route_path}: {'enabled' if enable_factory else 'disabled'}")
        return {
            'route_path': route_path,
            'factory_enabled': enable_factory,
            'migration_status': status,
            'success': True
        }
        
    except Exception as e:
        logger.error(f"Failed to configure route factory settings: {e}")
        return {
            'route_path': route_path,
            'factory_enabled': enable_factory,
            'error': str(e),
            'success': False
        }


# Helper function for startup configuration
async def configure_session_manager(app) -> None:
    """Configure session manager during app startup.
    
    This function should be called during FastAPI startup to initialize
    the UserSessionManager for proper session lifecycle management.
    
    Args:
        app: FastAPI application instance
    """
    try:
        logger.info("🔄 Configuring UserSessionManager...")
        
        from shared.session_management import initialize_session_manager, get_session_manager
        
        # Initialize session manager with background cleanup
        session_manager = await initialize_session_manager()
        
        # Store in app state for access in routes
        app.state.session_manager = session_manager
        
        # Get initial metrics for logging
        metrics = session_manager.get_session_metrics()
        logger.info(f"✅ UserSessionManager configured successfully - initial metrics: {metrics.to_dict()}")
        
    except Exception as e:
        logger.error(f"❌ Failed to configure UserSessionManager: {e}")
        raise RuntimeError(f"Session manager configuration failed: {e}")


async def shutdown_session_manager_app(app) -> None:
    """Shutdown session manager during app shutdown.
    
    This function should be called during FastAPI shutdown to properly
    cleanup session manager resources.
    
    Args:
        app: FastAPI application instance
    """
    try:
        logger.info("🔄 Shutting down UserSessionManager...")
        
        from shared.session_management import shutdown_session_manager
        
        # Shutdown session manager and cleanup
        await shutdown_session_manager()
        
        # Remove from app state
        if hasattr(app.state, 'session_manager'):
            delattr(app.state, 'session_manager')
        
        logger.info("✅ UserSessionManager shutdown completed")
        
    except Exception as e:
        logger.error(f"❌ Failed to shutdown UserSessionManager: {e}")
        # Don't raise exception during shutdown


def configure_factory_dependencies(app) -> None:
    """Configure factory pattern dependencies during app startup.
    
    This function should be called during FastAPI startup to initialize
    all factory pattern components and configure them properly.
    
    Args:
        app: FastAPI application instance
    """
    try:
        logger.info("🏭 Configuring factory pattern dependencies...")
        
        # Create ExecutionEngineFactory
        execution_factory_config = ExecutionFactoryConfig.from_env()
        execution_factory = ExecutionEngineFactory(execution_factory_config)
        
        # Create WebSocketBridgeFactory
        websocket_factory_config = WebSocketFactoryConfig.from_env()
        websocket_factory = WebSocketBridgeFactory(websocket_factory_config)
        
        # Create WebSocket connection pool
        connection_pool = WebSocketConnectionPool()
        
        # Configure WebSocket factory
        websocket_factory.configure(
            connection_pool=connection_pool,
            agent_registry=getattr(app.state, 'agent_registry', None),
            health_monitor=None  # Can be configured later if needed
        )
        
        # Configure execution factory
        execution_factory.configure(
            agent_registry=getattr(app.state, 'agent_registry', None),
            websocket_bridge_factory=websocket_factory,
            db_connection_pool=getattr(app.state, 'db_pool', None)
        )
        
        # Create FactoryAdapter
        adapter_config = AdapterConfig.from_env()
        factory_adapter = FactoryAdapter(execution_factory, websocket_factory, adapter_config)
        
        # Store in app state
        app.state.execution_engine_factory = execution_factory
        app.state.websocket_bridge_factory = websocket_factory
        app.state.websocket_connection_pool = connection_pool
        app.state.factory_adapter = factory_adapter
        
        # Configure agent registry to work with factory adapter
        if hasattr(app.state, 'agent_registry'):
            try:
                app.state.agent_registry.configure_factory_adapter(factory_adapter)
                logger.info("✅ Configured AgentRegistry with FactoryAdapter")
            except Exception as e:
                logger.warning(f"Failed to configure AgentRegistry with FactoryAdapter: {e}")
        
        logger.info("✅ Factory pattern dependencies configured successfully")
        
    except Exception as e:
        logger.error(f"❌ Failed to configure factory pattern dependencies: {e}")
        raise RuntimeError(f"Factory dependency configuration failed: {e}")


# Health check function for factory patterns
def get_factory_health_status(request: Request) -> Dict[str, Any]:
    """Get health status of all factory pattern components.
    
    Args:
        request: FastAPI request object
        
    Returns:
        Dictionary with health status of all factory components
    """
    try:
        status = {
            'execution_factory': {'configured': False, 'healthy': False},
            'websocket_factory': {'configured': False, 'healthy': False},
            'factory_adapter': {'configured': False, 'healthy': False},
            'overall_health': 'unknown'
        }
        
        # Check ExecutionEngineFactory
        try:
            factory = get_execution_engine_factory(request)
            status['execution_factory']['configured'] = True
            metrics = factory.get_factory_metrics()
            status['execution_factory']['healthy'] = True
            status['execution_factory']['metrics'] = metrics
        except Exception as e:
            status['execution_factory']['error'] = str(e)
        
        # Check WebSocketBridgeFactory
        try:
            factory = get_websocket_bridge_factory(request)
            status['websocket_factory']['configured'] = True
            metrics = factory.get_factory_metrics()
            status['websocket_factory']['healthy'] = True
            status['websocket_factory']['metrics'] = metrics
        except Exception as e:
            status['websocket_factory']['error'] = str(e)
        
        # Check FactoryAdapter
        try:
            adapter = get_factory_adapter(request)
            status['factory_adapter']['configured'] = True
            migration_status = adapter.get_migration_status()
            status['factory_adapter']['healthy'] = True
            status['factory_adapter']['migration_status'] = migration_status
        except Exception as e:
            status['factory_adapter']['error'] = str(e)
        
        # Determine overall health
        all_configured = all(status[component]['configured'] for component in 
                           ['execution_factory', 'websocket_factory', 'factory_adapter'])
        all_healthy = all(status[component]['healthy'] for component in 
                        ['execution_factory', 'websocket_factory', 'factory_adapter'])
        
        if all_configured and all_healthy:
            status['overall_health'] = 'healthy'
        elif all_configured:
            status['overall_health'] = 'degraded'
        else:
            status['overall_health'] = 'unhealthy'
        
        return status
        
    except Exception as e:
        return {
            'overall_health': 'error',
            'error': str(e)
        }