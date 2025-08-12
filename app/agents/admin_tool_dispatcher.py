# AI AGENT MODIFICATION METADATA
# ================================
# Timestamp: 2025-08-12T17:35:00.000000+00:00
# Agent: Claude Sonnet 4 claude-sonnet-4-20250514
# Context: Remove deprecated admin_tools.py dependency and integrate with unified tools
# Git: terra2 | bd8079c0 | modified
# Change: Refactor | Scope: Component | Risk: Medium
# Session: supervisor-consolidation | Seq: 2
# Review: Pending | Score: 88
# ================================
"""
Enhanced Tool Dispatcher with Admin Tools Integration

This module provides admin tool functionality through the unified tool registry
rather than the deprecated admin_tools.py module.
"""
from typing import List, Dict, Any, Optional
from langchain_core.tools import BaseTool
from sqlalchemy.orm import Session
from app.schemas import ToolResult, ToolStatus, ToolInput
from app.agents.tool_dispatcher import ToolDispatcher
# from app.agents.admin_tools import AdminToolRegistry  # DEPRECATED - using unified registry
from app.db.models_postgres import User
from app.services.permission_service import PermissionService
from app.logging_config import central_logger
import asyncio

logger = central_logger

class AdminToolDispatcher(ToolDispatcher):
    """Extended tool dispatcher that includes admin tools for privileged users"""
    
    def __init__(self, 
                 tools: List[BaseTool], 
                 db: Optional[Session] = None,
                 user: Optional[User] = None):
        """
        Initialize the admin tool dispatcher
        
        Args:
            tools: List of base tools available to all users
            db: Database session for admin operations
            user: Current user for permission checking
        """
        super().__init__(tools)
        
        self.db = db
        self.user = user
        self.admin_tools_enabled = False
        
        # Initialize admin tools if user has permissions
        if db and user:
            self._initialize_admin_tools()
    
    def _initialize_admin_tools(self):
        """Initialize admin tools based on user permissions"""
        if not self.user or not self.db:
            return
        
        # Check if user has admin/developer permissions
        if PermissionService.is_developer_or_higher(self.user):
            logger.info(f"Initializing admin tools for user {self.user.email}")
            self.admin_tools_enabled = True
            
            # Log available admin tools
            available_tools = self._get_available_admin_tools()
            logger.info(f"Admin tools available: {available_tools}")
        else:
            logger.debug(f"User {self.user.email} does not have admin permissions")
    
    async def dispatch(self, tool_name: str, **kwargs) -> ToolResult:
        """
        Dispatch tool execution with admin tool support
        
        Args:
            tool_name: Name of the tool to execute
            **kwargs: Tool arguments
            
        Returns:
            ToolResult with execution status and output
        """
        tool_input = ToolInput(tool_name=tool_name, kwargs=kwargs)
        
        # Check if it's an admin tool
        if self._is_admin_tool(tool_name):
            return await self._dispatch_admin_tool(tool_name, tool_input, **kwargs)
        
        # Otherwise use base dispatcher
        return await super().dispatch(tool_name, **kwargs)
    
    def _is_admin_tool(self, tool_name: str) -> bool:
        """Check if a tool is an admin tool"""
        admin_tools = [
            'corpus_manager',
            'synthetic_generator',
            'user_admin',
            'system_configurator',
            'log_analyzer'
        ]
        return tool_name in admin_tools
    
    async def _dispatch_admin_tool(self, 
                                   tool_name: str, 
                                   tool_input: ToolInput,
                                   **kwargs) -> ToolResult:
        """
        Dispatch admin tool execution with permission checking
        
        Args:
            tool_name: Name of the admin tool
            tool_input: Tool input object
            **kwargs: Tool arguments
            
        Returns:
            ToolResult with execution status
        """
        # Check if admin tools are initialized
        if not self.admin_tools_enabled:
            return ToolResult(
                tool_input=tool_input,
                status=ToolStatus.ERROR,
                message="Admin tools not available - insufficient permissions"
            )
        
        # Validate admin tool access
        if not self._validate_admin_tool_access(tool_name):
            return ToolResult(
                tool_input=tool_input,
                status=ToolStatus.ERROR,
                message=f"Admin tool {tool_name} not found or not accessible"
            )
        
        try:
            # Parse the action from kwargs
            action = kwargs.get('action', 'default')
            
            # Execute based on tool type and action
            if tool_name == 'corpus_manager':
                result = await self._execute_corpus_manager(action, **kwargs)
            elif tool_name == 'synthetic_generator':
                result = await self._execute_synthetic_generator(action, **kwargs)
            elif tool_name == 'user_admin':
                result = await self._execute_user_admin(action, **kwargs)
            elif tool_name == 'system_configurator':
                result = await self._execute_system_configurator(action, **kwargs)
            elif tool_name == 'log_analyzer':
                result = await self._execute_log_analyzer(action, **kwargs)
            else:
                result = {"error": f"Unknown admin tool: {tool_name}"}
            
            # Log successful admin action
            logger.info(f"Admin tool {tool_name} executed by {self.user.email}: {action}")
            
            return ToolResult(
                tool_input=tool_input,
                status=ToolStatus.SUCCESS,
                payload=result,
                metadata={
                    "admin_action": True,
                    "tool": tool_name,
                    "user": self.user.email,
                    "action": action
                }
            )
            
        except Exception as e:
            logger.error(f"Admin tool {tool_name} failed: {e}", exc_info=True)
            return ToolResult(
                tool_input=tool_input,
                status=ToolStatus.ERROR,
                message=str(e)
            )
    
    def _get_available_admin_tools(self) -> List[str]:
        """Get list of available admin tools for current user"""
        tools = []
        
        if PermissionService.has_permission(self.user, "corpus_write"):
            tools.append("corpus_manager")
        
        if PermissionService.has_permission(self.user, "synthetic_generate"):
            tools.append("synthetic_generator")
        
        if PermissionService.has_permission(self.user, "user_management"):
            tools.append("user_admin")
        
        if PermissionService.has_permission(self.user, "system_admin"):
            tools.extend(["system_configurator", "log_analyzer"])
        
        return tools
    
    def _validate_admin_tool_access(self, tool_name: str) -> bool:
        """Validate if user has access to specific admin tool"""
        permission_map = {
            "corpus_manager": "corpus_write",
            "synthetic_generator": "synthetic_generate", 
            "user_admin": "user_management",
            "system_configurator": "system_admin",
            "log_analyzer": "system_admin"
        }
        
        required_permission = permission_map.get(tool_name)
        if not required_permission:
            return False
        
        return PermissionService.has_permission(self.user, required_permission)
    
    async def _execute_corpus_manager(self, action: str, **kwargs) -> Dict[str, Any]:
        """Execute corpus manager actions via unified tool registry"""
        from app.services.unified_tool_registry import unified_tool_registry
        
        if action == 'create':
            domain = kwargs.get('domain', 'general')
            return await unified_tool_registry.execute_tool(
                'corpus_create', {'domain': domain, **kwargs}, self.user
            )
        elif action == 'list':
            return await unified_tool_registry.execute_tool(
                'corpus_list', {}, self.user
            )
        elif action == 'validate':
            corpus_id = kwargs.get('corpus_id')
            if not corpus_id:
                return {"error": "corpus_id required for validation"}
            return await unified_tool_registry.execute_tool(
                'corpus_validate', {'corpus_id': corpus_id}, self.user
            )
        else:
            return {"error": f"Unknown corpus action: {action}"}
    
    async def _execute_synthetic_generator(self, action: str, **kwargs) -> Dict[str, Any]:
        """Execute synthetic data generator actions via unified tool registry"""
        from app.services.unified_tool_registry import unified_tool_registry
        
        if action == 'generate':
            preset = kwargs.get('preset')
            corpus_id = kwargs.get('corpus_id')
            return await unified_tool_registry.execute_tool(
                'synthetic_generate', {
                    'preset': preset, 
                    'corpus_id': corpus_id, 
                    **kwargs
                }, self.user
            )
        elif action == 'list_presets':
            return await unified_tool_registry.execute_tool(
                'synthetic_list_presets', {}, self.user
            )
        else:
            return {"error": f"Unknown synthetic generator action: {action}"}
    
    async def _execute_user_admin(self, action: str, **kwargs) -> Dict[str, Any]:
        """Execute user admin actions via unified tool registry"""
        from app.services.unified_tool_registry import unified_tool_registry
        
        if action == 'create_user':
            email = kwargs.get('email')
            role = kwargs.get('role', 'standard_user')
            if not email:
                return {"error": "email required for user creation"}
            return await unified_tool_registry.execute_tool(
                'user_create', {'email': email, 'role': role, **kwargs}, self.user
            )
        elif action == 'grant_permission':
            user_email = kwargs.get('user_email')
            permission = kwargs.get('permission')
            if not user_email or not permission:
                return {"error": "user_email and permission required"}
            return await unified_tool_registry.execute_tool(
                'user_grant_permission', {
                    'user_email': user_email, 
                    'permission': permission
                }, self.user
            )
        else:
            return {"error": f"Unknown user admin action: {action}"}
    
    async def _execute_system_configurator(self, action: str, **kwargs) -> Dict[str, Any]:
        """Execute system configurator actions via unified tool registry"""
        from app.services.unified_tool_registry import unified_tool_registry
        
        if action == 'update_setting':
            setting_name = kwargs.get('setting_name')
            value = kwargs.get('value')
            if not setting_name:
                return {"error": "setting_name required"}
            return await unified_tool_registry.execute_tool(
                'system_update_setting', {
                    'setting_name': setting_name, 
                    'value': value
                }, self.user
            )
        else:
            return {"error": f"Unknown system configurator action: {action}"}
    
    async def _execute_log_analyzer(self, action: str, **kwargs) -> Dict[str, Any]:
        """Execute log analyzer actions via unified tool registry"""
        from app.services.unified_tool_registry import unified_tool_registry
        
        if action == 'analyze':
            query = kwargs.get('query', '')
            time_range = kwargs.get('time_range', '1h')
            return await unified_tool_registry.execute_tool(
                'log_analyze', {
                    'query': query, 
                    'time_range': time_range
                }, self.user
            )
        else:
            return {"error": f"Unknown log analyzer action: {action}"}
    
    def has_admin_access(self) -> bool:
        """Check if the current user has admin access"""
        return self.admin_tools_enabled
    
    def list_all_tools(self) -> List[str]:
        """List all available tools including admin tools"""
        base_tools = list(self.tools.keys())
        
        if self.admin_tools_enabled:
            admin_tools = self._get_available_admin_tools()
            return base_tools + admin_tools
        
        return base_tools
    
    def get_tool_info(self, tool_name: str) -> Dict[str, Any]:
        """Get information about a specific tool"""
        # Check if it's a base tool
        if tool_name in self.tools:
            tool = self.tools[tool_name]
            return {
                "name": tool_name,
                "type": "base",
                "description": getattr(tool, 'description', 'No description available'),
                "available": True
            }
        
        # Check if it's an admin tool
        if self._is_admin_tool(tool_name):
            if self.admin_tools_enabled and self._validate_admin_tool_access(tool_name):
                return {
                    "name": tool_name,
                    "type": "admin",
                    "description": f"Admin tool for {tool_name.replace('_', ' ')}",
                    "available": True,
                    "requires_permission": True
                }
            else:
                return {
                    "name": tool_name,
                    "type": "admin",
                    "available": False,
                    "reason": "Insufficient permissions"
                }
        
        return {
            "name": tool_name,
            "available": False,
            "reason": "Tool not found"
        }