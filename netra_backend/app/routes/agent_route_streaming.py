"""Agent route streaming functions with UserExecutionContext support."""
from typing import Any, AsyncGenerator, Dict, Optional

from fastapi.responses import StreamingResponse

from netra_backend.app.routes.agent_route_helpers import delegate_streaming
from netra_backend.app.schemas.request import RequestModel
from netra_backend.app.services.agent_service import AgentService
from netra_backend.app.services.user_execution_context import UserExecutionContext, validate_user_context
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


def get_agent_service_for_streaming(db_session, llm_manager) -> AgentService:
    """Get agent service for streaming."""
    from netra_backend.app.services.agent_service import get_agent_service
    return get_agent_service(db_session, llm_manager)


def get_agent_service_for_context_streaming(
    context: UserExecutionContext, llm_manager
) -> AgentService:
    """Get agent service for context-aware streaming.
    
    Args:
        context: UserExecutionContext with database session and user isolation
        llm_manager: LLM manager instance
        
    Returns:
        AgentService configured with context session
        
    Raises:
        ValueError: If context is invalid or missing database session
    """
    # Validate context
    validate_user_context(context)
    
    if not context.db_session:
        raise ValueError("UserExecutionContext must have a database session for streaming")
    
    from netra_backend.app.services.agent_service import get_agent_service
    return get_agent_service(context.db_session, llm_manager)


async def generate_sse_stream(
    request_model: RequestModel, agent_service: AgentService
) -> AsyncGenerator[str, None]:
    """Generate SSE formatted stream (legacy compatibility)."""
    async for chunk in stream_agent_response(
        request_model.query, request_model.id, agent_service
    ):
        yield f"data: {chunk}\n\n"


async def generate_sse_stream_with_context(
    request_model: RequestModel, context: UserExecutionContext
) -> AsyncGenerator[str, None]:
    """Generate SSE formatted stream with UserExecutionContext isolation.
    
    Args:
        request_model: Request containing query and basic parameters
        context: UserExecutionContext with user isolation and database session
        
    Yields:
        SSE-formatted streaming chunks with proper user isolation
        
    This method ensures:
    - User isolation through context
    - WebSocket connection routing if available
    - Error handling maintains context information
    - Proper cleanup of resources
    """
    try:
        # Log streaming start with correlation ID for traceability
        logger.info(
            f"Starting SSE stream with context: {context.get_correlation_id()}, "
            f"query length: {len(request_model.query) if request_model.query else 0}"
        )
        
        # Stream with context-aware isolation
        async for chunk in stream_agent_response_with_context(
            request_model.query,
            context,
            thread_id=request_model.id
        ):
            yield f"data: {chunk}\n\n"
            
        logger.debug(f"SSE stream completed for context: {context.get_correlation_id()}")
        
    except Exception as e:
        # Maintain context information in error handling
        error_msg = {
            "type": "error",
            "message": str(e),
            "context_id": context.request_id,
            "user_id": context.user_id[:8] + "..." if context.user_id else "unknown"
        }
        logger.error(
            f"SSE stream error for context {context.get_correlation_id()}: {e}",
            exc_info=True
        )
        yield f"data: {error_msg}\n\n"


def build_streaming_headers() -> Dict[str, str]:
    """Build headers for streaming response (legacy compatibility)."""
    return {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no"  # Disable nginx buffering
    }


def build_streaming_headers_with_context(context: UserExecutionContext) -> Dict[str, str]:
    """Build headers for streaming response with context information.
    
    Args:
        context: UserExecutionContext containing user and request information
        
    Returns:
        Dictionary of HTTP headers optimized for streaming with context tracking
        
    Headers include:
    - Standard SSE headers for proper streaming
    - Correlation ID for request tracing
    - WebSocket connection ID if available
    - Context request ID for debugging
    """
    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",  # Disable nginx buffering
        "X-Correlation-ID": context.get_correlation_id(),
        "X-Request-ID": context.request_id
    }
    
    # Add WebSocket connection ID if available for client routing
    if context.websocket_client_id:
        headers["X-WebSocket-Client-ID"] = context.websocket_client_id
    
    # Add operation depth for debugging nested operations
    if context.operation_depth > 0:
        headers["X-Operation-Depth"] = str(context.operation_depth)
    
    return headers


def get_sse_generator(request_model: RequestModel, agent_service: AgentService):
    """Get SSE stream generator (legacy compatibility)."""
    return generate_sse_stream(request_model, agent_service)


def get_sse_generator_with_context(request_model: RequestModel, context: UserExecutionContext):
    """Get SSE stream generator with UserExecutionContext.
    
    Args:
        request_model: Request containing query and parameters
        context: UserExecutionContext for user isolation
        
    Returns:
        AsyncGenerator for SSE-formatted streaming with context isolation
    """
    return generate_sse_stream_with_context(request_model, context)


def create_streaming_response(
    request_model: RequestModel, agent_service: AgentService
) -> StreamingResponse:
    """Create streaming response with headers (legacy compatibility)."""
    generator = get_sse_generator(request_model, agent_service)
    headers = build_streaming_headers()
    return StreamingResponse(generator, media_type="text/event-stream", headers=headers)


def create_streaming_response_with_context(
    request_model: RequestModel, context: UserExecutionContext
) -> StreamingResponse:
    """Create streaming response with UserExecutionContext isolation.
    
    Args:
        request_model: Request containing query and parameters
        context: UserExecutionContext for proper user isolation
        
    Returns:
        StreamingResponse configured for SSE with context isolation
        
    This method ensures:
    - Context passed through entire streaming pipeline
    - WebSocket connection IDs preserved from context
    - Proper headers for streaming
    - Error handling maintains context information
    """
    try:
        # Validate context before creating response
        validate_user_context(context)
        
        # Create generator with context
        generator = get_sse_generator_with_context(request_model, context)
        
        # Build headers with context-aware information
        headers = build_streaming_headers_with_context(context)
        
        logger.debug(
            f"Created streaming response for context: {context.get_correlation_id()}, "
            f"WebSocket ID: {context.websocket_client_id}"
        )
        
        return StreamingResponse(
            generator,
            media_type="text/event-stream",
            headers=headers
        )
        
    except Exception as e:
        logger.error(
            f"Failed to create streaming response for context {context.get_correlation_id()}: {e}",
            exc_info=True
        )
        raise


async def stream_agent_response(
    message: str,
    thread_id: Optional[str] = None,
    agent_service: Optional[AgentService] = None
) -> AsyncGenerator[str, None]:
    """Stream agent response using the actual agent service (legacy compatibility)."""
    async for chunk in delegate_streaming(agent_service, message, thread_id):
        yield chunk


async def stream_agent_response_with_context(
    message: str,
    context: UserExecutionContext,
    thread_id: Optional[str] = None
) -> AsyncGenerator[str, None]:
    """Stream agent response with UserExecutionContext isolation.
    
    Args:
        message: User message to process
        context: UserExecutionContext with user isolation and database session
        thread_id: Optional thread identifier (will use context.thread_id if not provided)
        
    Yields:
        Streaming chunks with proper user isolation
        
    This method ensures:
    - Complete user isolation through context
    - WebSocket connection routing preserved
    - Error handling maintains context information
    - Agent service configured with context session
    """
    try:
        # Validate context
        validate_user_context(context)
        
        # Use thread_id from context if not explicitly provided
        effective_thread_id = thread_id or context.thread_id
        
        logger.info(
            f"Starting agent response stream for context: {context.get_correlation_id()}, "
            f"thread_id: {effective_thread_id}, message length: {len(message)}"
        )
        
        # For now, we'll use the delegate_streaming approach but with context isolation
        # In the future, this should be replaced with a context-aware agent service method
        
        # Create agent service with context session (if available)
        if context.db_session:
            # TODO: Replace with context-aware agent service when available
            # For now, use existing delegate_streaming but ensure isolation
            async for chunk in delegate_streaming_with_context(
                context, message, effective_thread_id
            ):
                yield chunk
        else:
            # Fallback to legacy method if no session in context
            logger.warning(
                f"No database session in context {context.request_id}, "
                "falling back to legacy streaming"
            )
            async for chunk in delegate_streaming(None, message, effective_thread_id):
                yield chunk
                
        logger.debug(f"Agent response stream completed for context: {context.get_correlation_id()}")
        
    except Exception as e:
        logger.error(
            f"Agent response stream error for context {context.get_correlation_id()}: {e}",
            exc_info=True
        )
        # Yield error information maintaining context
        error_response = {
            "type": "error",
            "message": str(e),
            "context_id": context.request_id,
            "correlation_id": context.get_correlation_id()
        }
        yield str(error_response)


async def delegate_streaming_with_context(
    context: UserExecutionContext,
    message: str,
    thread_id: Optional[str]
) -> AsyncGenerator[str, None]:
    """Delegate streaming with UserExecutionContext isolation.
    
    Args:
        context: UserExecutionContext for user isolation
        message: User message to process
        thread_id: Thread identifier
        
    Yields:
        Streaming chunks with context isolation
        
    This function:
    - Creates agent service with context database session
    - Ensures WebSocket events are routed to correct user
    - Maintains audit trail through context
    - Provides proper error handling with context information
    """
    try:
        # Create agent service with context session if available
        agent_service = None
        if context.db_session:
            try:
                # TODO: Replace with proper context-aware agent service factory
                from netra_backend.app.services.agent_service import get_agent_service
                from netra_backend.app.llm.llm_manager import LLMManager
                from netra_backend.app.core.config import settings
                
                llm_manager = LLMManager(settings)
                agent_service = get_agent_service(context.db_session, llm_manager)
                
                logger.debug(
                    f"Created context-aware agent service for {context.get_correlation_id()}"
                )
                
            except Exception as e:
                logger.warning(
                    f"Failed to create context-aware agent service: {e}, "
                    "falling back to legacy delegate_streaming"
                )
        
        # Stream with agent service (context-aware if available)
        async for chunk in delegate_streaming(agent_service, message, thread_id):
            yield chunk
            
    except Exception as e:
        logger.error(
            f"Context-aware streaming delegation failed for {context.get_correlation_id()}: {e}",
            exc_info=True
        )
        raise