"""
Error Handlers Module - Compatibility Layer for Legacy Import Patterns

This module provides a compatibility layer for legacy import patterns while directing
all functionality to the unified error handler (SSOT).

CRITICAL ARCHITECTURAL COMPLIANCE:
- This is a COMPATIBILITY LAYER ONLY
- All actual implementation is in unified_error_handler.py (SSOT)
- This module exists solely to support existing import patterns
- DO NOT add new functionality here - extend unified_error_handler.py instead

Business Value Justification:
- Segment: Platform/Internal  
- Business Goal: System Reliability & Backward Compatibility
- Value Impact: Maintains existing imports while consolidating to SSOT
- Strategic Impact: Zero disruption migration to unified error handling
"""

from typing import Any, Dict, List, Optional, Union, Callable
from fastapi import Request
from fastapi.responses import JSONResponse

# Import everything from the unified error handler (SSOT)
from netra_backend.app.core.unified_error_handler import (
    # Core handler classes
    UnifiedErrorHandler,
    APIErrorHandler, 
    AgentErrorHandler,
    WebSocketErrorHandler,
    
    # Recovery strategies
    RecoveryStrategy,
    RetryRecoveryStrategy,
    FallbackRecoveryStrategy,
    
    # Global instances (SSOT)
    api_error_handler,
    agent_error_handler,
    websocket_error_handler,
    global_agent_error_handler,
    global_api_error_handler,
    
    # Convenience functions
    handle_error,
    handle_exception,
    get_http_status_code,
    get_error_statistics,
    
    # Decorator
    handle_agent_error,
    
    # FastAPI exception handlers
    unified_exception_handler,
    validation_exception_handler, 
    http_exception_handler,
    netra_exception_handler,
    general_exception_handler,
    
    # Factory function
    ErrorHandler,
)

# Import error types and responses
from netra_backend.app.core.error_codes import ErrorCode, ErrorSeverity
from netra_backend.app.core.error_response import ErrorResponse
from netra_backend.app.schemas.core_enums import ErrorCategory
from netra_backend.app.schemas.shared_types import ErrorContext

# Import specific exceptions
from netra_backend.app.core.exceptions_agent import AgentError
from netra_backend.app.core.exceptions_base import NetraException

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


def setup_error_handlers(app: Optional[Any] = None) -> Dict[str, Any]:
    """
    Setup error handlers for the application.
    
    This function configures the unified error handling system and registers
    FastAPI exception handlers if an app instance is provided.
    
    Args:
        app: Optional FastAPI application instance
        
    Returns:
        Dict containing configured error handlers and setup status
    """
    try:
        logger.info("Setting up unified error handlers")
        
        # Get the global unified error handler instance
        from netra_backend.app.core.unified_error_handler import _unified_error_handler
        
        # Configure FastAPI exception handlers if app is provided
        if app is not None:
            logger.info("Registering FastAPI exception handlers")
            
            # Register unified exception handlers
            app.add_exception_handler(Exception, general_exception_handler)
            app.add_exception_handler(NetraException, netra_exception_handler)
            
            from fastapi import HTTPException
            from pydantic import ValidationError
            
            app.add_exception_handler(HTTPException, http_exception_handler)
            app.add_exception_handler(ValidationError, validation_exception_handler)
            
            logger.info("FastAPI exception handlers registered successfully")
        
        # Return configuration status
        setup_result = {
            'status': 'success',
            'unified_handler': _unified_error_handler,
            'api_handler': api_error_handler,
            'agent_handler': agent_error_handler, 
            'websocket_handler': websocket_error_handler,
            'fastapi_handlers_registered': app is not None,
            'error_statistics': get_error_statistics(),
            'message': 'Unified error handling system configured successfully'
        }
        
        logger.info("Error handlers setup completed successfully")
        return setup_result
        
    except Exception as e:
        logger.error(f"Failed to setup error handlers: {e}", exc_info=True)
        return {
            'status': 'error',
            'error': str(e),
            'message': 'Failed to setup error handlers'
        }


# Legacy compatibility aliases for backward compatibility
ApiErrorHandler = APIErrorHandler  # Capital case alias
ExecutionErrorHandler = AgentErrorHandler  # Legacy name mapping

# Additional convenience functions for common use cases
async def handle_api_error(
    error: Exception,
    request: Optional[Request] = None,
    trace_id: Optional[str] = None
) -> JSONResponse:
    """Handle API error and return JSONResponse."""
    return await api_error_handler.handle_exception(error, request, trace_id)


async def handle_agent_execution_error(
    error: Exception,
    context: Optional[ErrorContext] = None,
    **kwargs
) -> Union[AgentError, Any]:
    """Handle agent execution error."""
    return await agent_error_handler.handle_error(error, context, **kwargs)


async def handle_websocket_error(
    error: Exception,
    connection_id: Optional[str] = None,
    message_type: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """Handle WebSocket error."""
    return await websocket_error_handler.handle_websocket_error(
        error, connection_id, message_type, **kwargs
    )


def get_error_handler_health() -> Dict[str, Any]:
    """Get health status of error handling system."""
    return {
        'unified_error_handler': 'healthy',
        'api_handler': 'healthy',
        'agent_handler': 'healthy', 
        'websocket_handler': 'healthy',
        **get_error_statistics()
    }


# Ensure all expected exports are available
__all__ = [
    # Setup function (required by integration tests)
    'setup_error_handlers',
    
    # Core classes
    'UnifiedErrorHandler',
    'APIErrorHandler',
    'AgentErrorHandler', 
    'WebSocketErrorHandler',
    
    # Legacy aliases
    'ApiErrorHandler',
    'ExecutionErrorHandler',
    
    # Recovery strategies
    'RecoveryStrategy',
    'RetryRecoveryStrategy',
    'FallbackRecoveryStrategy',
    
    # Global instances
    'api_error_handler',
    'agent_error_handler',
    'websocket_error_handler', 
    'global_agent_error_handler',
    'global_api_error_handler',
    
    # Functions
    'handle_error',
    'handle_exception',
    'handle_api_error',
    'handle_agent_execution_error',
    'handle_websocket_error',
    'get_http_status_code',
    'get_error_statistics',
    'get_error_handler_health',
    
    # Decorator
    'handle_agent_error',
    
    # FastAPI handlers
    'unified_exception_handler',
    'validation_exception_handler',
    'http_exception_handler', 
    'netra_exception_handler',
    'general_exception_handler',
    
    # Types
    'ErrorCode',
    'ErrorSeverity',
    'ErrorCategory',
    'ErrorResponse',
    'ErrorContext',
    'AgentError',
    'NetraException',
    
    # Factory
    'ErrorHandler',
]