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
from typing import Optional
from sqlalchemy.orm import Session
from app.db.models_postgres import User
from app.agents.supervisor import SupervisorAgent, SupervisorMode, SupervisorConfig, create_supervisor
from app.agents.admin_tool_dispatcher import AdminToolDispatcher
from app.agents.tool_dispatcher import ToolDispatcher
from app.llm.llm_manager import LLMManager
from app.services.permission_service import PermissionService
from app.logging_config import central_logger
from langchain_core.tools import BaseTool
from typing import List

logger = central_logger

def create_supervisor_with_admin_support(
    llm_manager: LLMManager,
    tools: List[BaseTool],
    db: Optional[Session] = None,
    user: Optional[User] = None,
    websocket_manager=None,
    thread_id: Optional[str] = None,
    enable_quality_gates: bool = False
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
        
    Returns:
        Configured SupervisorAgent instance
    """
    
    # Determine supervisor mode and tool dispatcher
    has_admin_access = db and user and PermissionService.is_developer_or_higher(user)
    
    if has_admin_access:
        logger.info(f"Creating supervisor with admin tools for user {user.email}")
        tool_dispatcher = AdminToolDispatcher(tools, db, user)
        mode = SupervisorMode.ADMIN_ENABLED
        
        # Log available admin tools
        admin_tools = tool_dispatcher.list_all_tools()
        logger.info(f"Total tools available (including admin): {len(admin_tools)}")
    else:
        logger.info("Creating supervisor with standard tools only")
        tool_dispatcher = ToolDispatcher(tools)
        mode = SupervisorMode.QUALITY_ENHANCED if enable_quality_gates else SupervisorMode.BASIC
    
    # Create supervisor configuration
    config = SupervisorConfig(
        mode=mode,
        enable_quality_gates=enable_quality_gates,
        enable_admin_tools=has_admin_access,
        enable_circuit_breaker=True
    )
    
    # Create unified supervisor agent
    supervisor = SupervisorAgent(
        db_session=db,
        llm_manager=llm_manager,
        websocket_manager=websocket_manager,
        tool_dispatcher=tool_dispatcher,
        config=config,
        user_id=str(user.id) if user else None,
        thread_id=thread_id
    )
    
    return supervisor


def check_admin_command(message: str) -> Optional[str]:
    """
    Check if a message is an admin command
    
    Args:
        message: User message to check
        
    Returns:
        Admin command type if detected, None otherwise
    """
    admin_commands = {
        '/corpus': 'corpus',
        '/synthetic': 'synthetic',
        '/users': 'users',
        '/config': 'config',
        '/logs': 'logs'
    }
    
    # Check if message starts with any admin command
    for command, cmd_type in admin_commands.items():
        if message.lower().startswith(command):
            return cmd_type
    
    # Check for natural language admin requests
    admin_keywords = {
        'corpus': ['create corpus', 'manage corpus', 'corpus management'],
        'synthetic': ['generate synthetic', 'synthetic data', 'test data'],
        'users': ['create user', 'manage users', 'user permissions'],
        'config': ['system setting', 'configuration', 'update config'],
        'logs': ['analyze logs', 'show logs', 'log analysis']
    }
    
    message_lower = message.lower()
    for cmd_type, keywords in admin_keywords.items():
        if any(keyword in message_lower for keyword in keywords):
            return cmd_type
    
    return None


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
    
    # Check if supervisor has admin capabilities
    if not hasattr(supervisor.tool_dispatcher, 'has_admin_access'):
        return {
            "status": "error",
            "message": "Admin tools not available"
        }
    
    if not supervisor.tool_dispatcher.has_admin_access():
        return {
            "status": "error",
            "message": "Insufficient permissions for admin operations"
        }
    
    # Route to appropriate admin agent based on command type
    agent_mapping = {
        'corpus': 'corpus_admin',
        'synthetic': 'synthetic_data',
        'users': 'user_admin',
        'config': 'system_config',
        'logs': 'log_analyzer'
    }
    
    target_agent = agent_mapping.get(command_type)
    
    if not target_agent:
        return {
            "status": "error",
            "message": f"Unknown admin command type: {command_type}"
        }
    
    # Execute through supervisor with admin context
    try:
        state = await supervisor.run(
            user_request=message,
            run_id=run_id,
            stream_updates=stream_updates
        )
        
        return {
            "status": "success",
            "state": state,
            "admin_action": command_type,
            "circuit_breaker_status": supervisor.circuit_breaker_status
        }
        
    except Exception as e:
        logger.error(f"Admin request failed: {e}", exc_info=True)
        return {
            "status": "error",
            "message": str(e)
        }