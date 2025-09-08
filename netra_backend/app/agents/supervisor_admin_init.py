# AI AGENT MODIFICATION METADATA
# ================================
# Timestamp: 2025-08-12T17:40:00.000000+00:00
# Agent: Claude Sonnet 4 claude-sonnet-4-20250514
# Context: Update to use unified supervisor with admin support
# Git: terra2 | bd8079c0 | modified
# Change: Refactor | Scope: Component | Risk: Medium
# Session: supervisor-consolidation | Seq: 3
# Review: Pending | Score: 87
# ================================
"""
Supervisor Agent Initialization with Admin Tool Support

This module provides factory functions for creating supervisor agents
with admin tool support using the unified supervisor architecture.
"""
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

from langchain_core.tools import BaseTool
from sqlalchemy.ext.asyncio import AsyncSession

# NOTE: AdminToolDispatcher modules were deleted - functions using them are disabled
# from netra_backend.app.agents.admin_tool_dispatcher import AdminToolDispatcher
# from netra_backend.app.agents.admin_tool_dispatcher.migration_helper import (
#     AdminToolDispatcherMigrationHelper,
#     upgrade_admin_dispatcher_creation
# )
from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcher
from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext
from netra_backend.app.db.models_postgres import User
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.logging_config import central_logger
from netra_backend.app.services.permission_service import PermissionService

logger = central_logger


class SupervisorMode(Enum):
    """Supervisor operation modes."""
    BASIC = "basic"
    QUALITY_ENHANCED = "quality_enhanced" 
    ADMIN_ENABLED = "admin_enabled"


@dataclass
class SupervisorConfig:
    """Configuration for supervisor agent."""
    mode: SupervisorMode
    enable_quality_gates: bool = False
    enable_admin_tools: bool = False
    enable_circuit_breaker: bool = True


def _determine_admin_access(db: Optional[AsyncSession], user: Optional[User]) -> bool:
    """Determine if user has admin access."""
    if not db or not user:
        return False
    return PermissionService.is_developer_or_higher(user)


async def _create_admin_tool_dispatcher(
    tools: List[BaseTool], 
    db: AsyncSession, 
    user: User,
    user_context: Optional[UserExecutionContext] = None
):
    """DISABLED: AdminToolDispatcher modules were deleted.
    
    Args:
        tools: List of tools to register
        db: Database session
        user: Admin user
        user_context: Optional UserExecutionContext (recommended for proper isolation)
        
    Raises:
        NotImplementedError: AdminToolDispatcher was deleted
    """
    logger.error(f"AdminToolDispatcher functionality disabled for user {user.email} - modules were deleted")
    raise NotImplementedError(
        "AdminToolDispatcher modules were deleted. This functionality is temporarily disabled "
        "until the modules are restored or replaced."
    )


def _create_standard_tool_dispatcher(
    tools: List[BaseTool],
    user_context: Optional[UserExecutionContext] = None
) -> UnifiedToolDispatcher:
    """Create standard tool dispatcher with optional request-scoped context.
    
    Args:
        tools: List of tools to register
        user_context: Optional UserExecutionContext for request-scoped isolation
        
    Returns:
        UnifiedToolDispatcher: Tool dispatcher (request-scoped if context provided)
    """
    logger.info("Creating supervisor with standard tools only")
    
    if user_context:
        logger.info("✅ Creating request-scoped standard tool dispatcher")
        # Modern request-scoped pattern
        return UnifiedToolDispatcher(user_context=user_context, tools=tools)
    else:
        logger.warning("⚠️ Creating global tool dispatcher - consider providing UserExecutionContext")
        # Legacy global pattern with warning
        return UnifiedToolDispatcher(user_context=None, tools=tools)


def _determine_supervisor_mode(has_admin_access: bool, enable_quality_gates: bool) -> SupervisorMode:
    """Determine appropriate supervisor mode."""
    if has_admin_access:
        return SupervisorMode.ADMIN_ENABLED
    return SupervisorMode.QUALITY_ENHANCED if enable_quality_gates else SupervisorMode.BASIC


def _create_supervisor_config(mode: SupervisorMode, enable_quality_gates: bool, has_admin_access: bool) -> SupervisorConfig:
    """Create supervisor configuration."""
    return SupervisorConfig(
        mode=mode,
        enable_quality_gates=enable_quality_gates,
        enable_admin_tools=has_admin_access,
        enable_circuit_breaker=True
    )


def _create_supervisor_instance(
    db: Optional[AsyncSession],
    llm_manager: LLMManager,
    websocket_manager,
    tool_dispatcher,
    config: SupervisorConfig,
    user: Optional[User],
    thread_id: Optional[str]
) -> SupervisorAgent:
    """Create supervisor agent instance."""
    from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
    
    # Create proper websocket bridge instead of passing websocket_manager
    websocket_bridge = AgentWebSocketBridge() if websocket_manager else None
    
    return SupervisorAgent(
        db_session=db,
        llm_manager=llm_manager,
        websocket_bridge=websocket_bridge,  # Proper AgentWebSocketBridge instance
        tool_dispatcher=tool_dispatcher
        # Note: config, user_id, thread_id are not part of SupervisorAgent constructor
    )


async def create_supervisor_with_admin_support(
    llm_manager: LLMManager,
    tools: List[BaseTool],
    db: Optional[AsyncSession] = None,
    user: Optional[User] = None,
    websocket_manager=None,
    thread_id: Optional[str] = None,
    enable_quality_gates: bool = False,
    user_context: Optional[UserExecutionContext] = None
) -> SupervisorAgent:
    """
    Create a supervisor agent with admin tool support based on user permissions
    
    Args:
        llm_manager: LLM manager instance
        tools: List of base tools
        db: Database session
        user: Current user
        websocket_manager: WebSocket manager for real-time updates
        thread_id: Thread ID for context
        enable_quality_gates: Whether to enable quality gates
        user_context: Optional UserExecutionContext for request isolation (RECOMMENDED)
        
    Returns:
        Configured SupervisorAgent instance
    """
    has_admin_access = _determine_admin_access(db, user)
    tool_dispatcher = await _setup_tool_dispatcher(tools, db, user, has_admin_access, user_context)
    supervisor_config = _setup_supervisor_configuration(has_admin_access, enable_quality_gates)
    return _create_supervisor_instance(db, llm_manager, websocket_manager, tool_dispatcher, supervisor_config, user, thread_id)

async def _setup_tool_dispatcher(
    tools: List[BaseTool], 
    db: Optional[AsyncSession], 
    user: Optional[User], 
    has_admin_access: bool,
    user_context: Optional[UserExecutionContext] = None
):
    """Setup appropriate tool dispatcher based on admin access.
    
    Args:
        tools: List of tools to register
        db: Database session
        user: Current user
        has_admin_access: Whether user has admin access
        user_context: Optional UserExecutionContext for request isolation
        
    Returns:
        Tool dispatcher (admin or standard)
    """
    if has_admin_access:
        return await _create_admin_tool_dispatcher(tools, db, user, user_context)
    return _create_standard_tool_dispatcher(tools, user_context)

def _setup_supervisor_configuration(has_admin_access: bool, enable_quality_gates: bool) -> SupervisorConfig:
    """Setup supervisor configuration based on access level."""
    mode = _determine_supervisor_mode(has_admin_access, enable_quality_gates)
    return _create_supervisor_config(mode, enable_quality_gates, has_admin_access)


def check_admin_command(message: str) -> Optional[str]:
    """
    Check if a message is an admin command
    
    Args:
        message: User message to check
        
    Returns:
        Admin command type if detected, None otherwise
    """
    direct_command_result = _check_direct_admin_commands(message)
    if direct_command_result:
        return direct_command_result
    return _check_natural_language_admin_commands(message)

def _check_direct_admin_commands(message: str) -> Optional[str]:
    """Check for direct admin command patterns."""
    admin_commands = _get_direct_admin_commands()
    message_lower = message.lower()
    for command, cmd_type in admin_commands.items():
        if message_lower.startswith(command):
            return cmd_type
    return None

def _get_direct_admin_commands() -> dict:
    """Get mapping of direct admin commands."""
    return {
        '/corpus': 'corpus',
        '/synthetic': 'synthetic',
        '/users': 'users',
        '/config': 'config',
        '/logs': 'logs'
    }

def _check_natural_language_admin_commands(message: str) -> Optional[str]:
    """Check for natural language admin command patterns."""
    admin_keywords = _get_admin_keyword_mapping()
    message_lower = message.lower()
    for cmd_type, keywords in admin_keywords.items():
        if _message_contains_keywords(message_lower, keywords):
            return cmd_type
    return None

def _get_admin_keyword_mapping() -> dict:
    """Get mapping of admin command types to keywords."""
    return {
        'corpus': ['create corpus', 'manage corpus', 'corpus management'],
        'synthetic': ['generate synthetic', 'synthetic data', 'test data'],
        'users': ['create user', 'manage users', 'user permissions'],
        'config': ['system setting', 'configuration', 'update config'],
        'logs': ['analyze logs', 'show logs', 'log analysis']
    }

def _message_contains_keywords(message_lower: str, keywords: List[str]) -> bool:
    """Check if message contains any of the specified keywords."""
    return any(keyword in message_lower for keyword in keywords)


async def handle_admin_request(
    supervisor: SupervisorAgent,
    message: str,
    command_type: str,
    run_id: str,
    stream_updates: bool = True
) -> dict:
    """
    Handle an admin request through the supervisor
    
    Args:
        supervisor: Supervisor agent instance
        message: User message
        command_type: Type of admin command
        run_id: Run ID for tracking
        stream_updates: Whether to stream updates
        
    Returns:
        Result dictionary
    """
    # Validate admin permissions
    admin_check_result = _check_admin_permissions(supervisor)
    if admin_check_result:
        return admin_check_result
    
    # Validate command type
    command_validation_result = _validate_command_type(command_type)
    if command_validation_result:
        return command_validation_result
    
    # Execute admin request
    try:
        return await _execute_admin_request(supervisor, message, run_id, stream_updates, command_type)
    except Exception as e:
        return _handle_admin_request_error(e)


def _check_admin_permissions(supervisor: SupervisorAgent) -> Optional[dict]:
    """Check if supervisor has admin permissions."""
    if not hasattr(supervisor.tool_dispatcher, 'has_admin_access'):
        return {"status": "error", "message": "Admin tools not available"}
    
    if not supervisor.tool_dispatcher.has_admin_access():
        return {"status": "error", "message": "Insufficient permissions for admin operations"}
    
    return None


def _get_agent_mapping() -> dict:
    """Get mapping of command types to agent names."""
    return {
        'corpus': 'corpus_admin',
        'synthetic': 'synthetic_data',
        'users': 'user_admin',
        'config': 'system_config',
        'logs': 'log_analyzer'
    }


def _validate_command_type(command_type: str) -> Optional[dict]:
    """Validate that command type is supported."""
    agent_mapping = _get_agent_mapping()
    target_agent = agent_mapping.get(command_type)
    
    if not target_agent:
        return {
            "status": "error",
            "message": f"Unknown admin command type: {command_type}"
        }
    return None


async def _execute_admin_request(
    supervisor: SupervisorAgent,
    message: str,
    run_id: str,
    stream_updates: bool,
    command_type: str
) -> dict:
    """Execute the admin request through supervisor."""
    state = await supervisor.run(
        user_request=message,
        run_id=run_id,
        stream_updates=stream_updates
    )
    
    return _create_success_response(state, command_type, supervisor)


def _create_success_response(state, command_type: str, supervisor: SupervisorAgent) -> dict:
    """Create successful admin request response."""
    return {
        "status": "success",
        "state": state,
        "admin_action": command_type,
        "circuit_breaker_status": supervisor.circuit_breaker_status
    }


def _handle_admin_request_error(e: Exception) -> dict:
    """Handle admin request execution errors."""
    logger.error(f"Admin request failed: {e}", exc_info=True)
    return {
        "status": "error",
        "message": str(e)
    }