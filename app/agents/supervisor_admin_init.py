"""
Supervisor Agent Initialization with Admin Tool Support
"""
from typing import Optional
from sqlalchemy.orm import Session
from app.db.models_postgres import User
from app.agents.supervisor_consolidated import SupervisorAgent
from app.agents.admin_tool_dispatcher import AdminToolDispatcher
from app.agents.tool_dispatcher import ToolDispatcher
from app.llm.llm_manager import LLMManager
from app.services.permission_service import PermissionService
from app.core.logging_config import central_logger
from langchain_core.tools import BaseTool
from typing import List

logger = central_logger

def create_supervisor_with_admin_support(
    llm_manager: LLMManager,
    tools: List[BaseTool],
    db: Optional[Session] = None,
    user: Optional[User] = None,
    websocket_manager=None,
    thread_id: Optional[str] = None
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
    
    # Determine which tool dispatcher to use
    if db and user and PermissionService.is_developer_or_higher(user):
        logger.info(f"Creating supervisor with admin tools for user {user.email}")
        tool_dispatcher = AdminToolDispatcher(tools, db, user)
        
        # Log available admin tools
        admin_tools = tool_dispatcher.list_all_tools()
        logger.info(f"Total tools available (including admin): {len(admin_tools)}")
    else:
        logger.info("Creating supervisor with standard tools only")
        tool_dispatcher = ToolDispatcher(tools)
    
    # Create supervisor agent
    supervisor = SupervisorAgent(
        llm_manager=llm_manager,
        tool_dispatcher=tool_dispatcher
    )
    
    # Set additional context if provided
    if websocket_manager:
        supervisor.websocket_manager = websocket_manager
    
    if thread_id:
        supervisor.thread_id = thread_id
    
    if db:
        supervisor.db_session = db
    
    if user:
        supervisor.user_id = user.id
        
        # Set admin context if user has privileges
        if PermissionService.is_developer_or_higher(user):
            supervisor.metadata = supervisor.metadata or {}
            supervisor.metadata["is_admin"] = True
            supervisor.metadata["user_role"] = user.role
            supervisor.metadata["user_email"] = user.email
    
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
        state = await supervisor.execute(
            user_request=message,
            run_id=run_id,
            stream_updates=stream_updates,
            metadata={
                "admin_request": True,
                "command_type": command_type,
                "target_agent": target_agent
            }
        )
        
        return {
            "status": "success",
            "state": state,
            "admin_action": command_type
        }
        
    except Exception as e:
        logger.error(f"Admin request failed: {e}", exc_info=True)
        return {
            "status": "error",
            "message": str(e)
        }