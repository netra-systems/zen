"""Prerequisites Validator Compatibility Module

CRITICAL: This module provides backward compatibility for tests expecting 
the prerequisites_validator module name.

All functionality is re-exported from agent_execution_prerequisites module
to maintain test compatibility while providing the main implementation.

Resolves Issue #387 - Agent Execution Prerequisites Missing Validation
"""

import asyncio
from typing import Dict, Any

# Re-export everything from the main implementation
from netra_backend.app.agents.supervisor.agent_execution_prerequisites import (
    # Main classes
    AgentExecutionPrerequisites,
    PrerequisiteValidationResult,
    PrerequisiteValidationLevel,
    PrerequisiteCategory,
    
    # Exception classes
    AgentExecutionPrerequisiteError,
    WebSocketPrerequisiteError,
    DatabasePrerequisiteError,
    UserContextPrerequisiteError,
    ResourceLimitPrerequisiteError,
    
    # Individual validation functions
    validate_websocket_connection_available as _async_validate_websocket_connection_available,
    validate_websocket_events_ready as _async_validate_websocket_events_ready,
    validate_websocket_manager_initialized as _async_validate_websocket_manager_initialized,
    validate_database_connectivity as _async_validate_database_connectivity,
    validate_clickhouse_availability as _async_validate_clickhouse_availability,
    validate_postgres_availability as _async_validate_postgres_availability,
    validate_redis_availability as _async_validate_redis_availability,
    validate_external_services as _async_validate_external_services,
    validate_agent_registry_initialized as _async_validate_agent_registry_initialized,
    validate_agent_availability as _async_validate_agent_availability,
    validate_user_context_integrity as _async_validate_user_context_integrity,
    validate_user_permissions as _async_validate_user_permissions,
    validate_user_resource_limits as _async_validate_user_resource_limits,
    validate_system_resource_availability as _async_validate_system_resource_availability,
    
    # Main validation function
    validate_all_agent_execution_prerequisites
)

# Create a convenience class alias for tests expecting PrerequisiteValidator
PrerequisiteValidator = AgentExecutionPrerequisites

# Main validation function alias for compatibility
async def validate_all_prerequisites(execution_context, user_context, 
                                   validation_level=PrerequisiteValidationLevel.STRICT):
    """Compatibility function for tests expecting validate_all_prerequisites."""
    return await validate_all_agent_execution_prerequisites(
        execution_context, user_context, validation_level
    )

# === SYNCHRONOUS WRAPPERS FOR TEST COMPATIBILITY ===

def validate_websocket_connection_available() -> Dict[str, Any]:
    """Synchronous wrapper for validate_websocket_connection_available."""
    try:
        return asyncio.run(_async_validate_websocket_connection_available())
    except RuntimeError:
        # If no event loop, create one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(_async_validate_websocket_connection_available())
        finally:
            loop.close()

def validate_websocket_events_ready() -> Dict[str, Any]:
    """Synchronous wrapper for validate_websocket_events_ready."""
    try:
        return asyncio.run(_async_validate_websocket_events_ready())
    except RuntimeError:
        # If no event loop, create one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(_async_validate_websocket_events_ready())
        finally:
            loop.close()

def validate_websocket_manager_initialized() -> Dict[str, Any]:
    """Synchronous wrapper for validate_websocket_manager_initialized."""
    try:
        return asyncio.run(_async_validate_websocket_manager_initialized())
    except RuntimeError:
        # If no event loop, create one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(_async_validate_websocket_manager_initialized())
        finally:
            loop.close()

def validate_database_connectivity() -> Dict[str, Any]:
    """Synchronous wrapper for validate_database_connectivity."""
    try:
        return asyncio.run(_async_validate_database_connectivity())
    except RuntimeError:
        # If no event loop, create one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(_async_validate_database_connectivity())
        finally:
            loop.close()

def validate_clickhouse_availability() -> Dict[str, Any]:
    """Synchronous wrapper for validate_clickhouse_availability."""
    try:
        return asyncio.run(_async_validate_clickhouse_availability())
    except RuntimeError:
        # If no event loop, create one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(_async_validate_clickhouse_availability())
        finally:
            loop.close()

def validate_postgres_availability() -> Dict[str, Any]:
    """Synchronous wrapper for validate_postgres_availability."""
    try:
        return asyncio.run(_async_validate_postgres_availability())
    except RuntimeError:
        # If no event loop, create one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(_async_validate_postgres_availability())
        finally:
            loop.close()

def validate_redis_availability() -> Dict[str, Any]:
    """Synchronous wrapper for validate_redis_availability."""
    try:
        return asyncio.run(_async_validate_redis_availability())
    except RuntimeError:
        # If no event loop, create one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(_async_validate_redis_availability())
        finally:
            loop.close()

def validate_external_services() -> Dict[str, Any]:
    """Synchronous wrapper for validate_external_services."""
    try:
        return asyncio.run(_async_validate_external_services())
    except RuntimeError:
        # If no event loop, create one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(_async_validate_external_services())
        finally:
            loop.close()

def validate_agent_registry_initialized() -> Dict[str, Any]:
    """Synchronous wrapper for validate_agent_registry_initialized."""
    try:
        return asyncio.run(_async_validate_agent_registry_initialized())
    except RuntimeError:
        # If no event loop, create one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(_async_validate_agent_registry_initialized())
        finally:
            loop.close()

def validate_agent_availability(agent_name: str) -> Dict[str, Any]:
    """Synchronous wrapper for validate_agent_availability."""
    try:
        return asyncio.run(_async_validate_agent_availability(agent_name))
    except RuntimeError:
        # If no event loop, create one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(_async_validate_agent_availability(agent_name))
        finally:
            loop.close()

def validate_user_context_integrity(user_context) -> Dict[str, Any]:
    """Synchronous wrapper for validate_user_context_integrity."""
    try:
        return asyncio.run(_async_validate_user_context_integrity(user_context))
    except RuntimeError:
        # If no event loop, create one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(_async_validate_user_context_integrity(user_context))
        finally:
            loop.close()

def validate_user_permissions(user_context) -> Dict[str, Any]:
    """Synchronous wrapper for validate_user_permissions."""
    try:
        return asyncio.run(_async_validate_user_permissions(user_context))
    except RuntimeError:
        # If no event loop, create one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(_async_validate_user_permissions(user_context))
        finally:
            loop.close()

def validate_user_resource_limits(user_context) -> Dict[str, Any]:
    """Synchronous wrapper for validate_user_resource_limits."""
    try:
        return asyncio.run(_async_validate_user_resource_limits(user_context))
    except RuntimeError:
        # If no event loop, create one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(_async_validate_user_resource_limits(user_context))
        finally:
            loop.close()

def validate_system_resource_availability() -> Dict[str, Any]:
    """Synchronous wrapper for validate_system_resource_availability."""
    try:
        return asyncio.run(_async_validate_system_resource_availability())
    except RuntimeError:
        # If no event loop, create one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(_async_validate_system_resource_availability())
        finally:
            loop.close()