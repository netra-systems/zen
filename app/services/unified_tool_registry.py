"""
Unified Tool Registry - Central registry for all tools with permission-based access
"""
from typing import Dict, List, Optional, Any, Callable, Union
from datetime import datetime
import inspect
import json
from sqlalchemy.orm import Session
from app.schemas.ToolPermission import ToolExecutionContext, PermissionCheckResult
from app.schemas.UserPlan import UserPlan
from app.services.tool_permission_service import ToolPermissionService
from app.db.models_postgres import User
from app.logging_config import central_logger
from app.core.exceptions import NetraException
from pydantic import BaseModel, Field

logger = central_logger


class UnifiedTool(BaseModel):
    """Unified tool definition"""
    name: str = Field(description="Unique tool identifier")
    description: str = Field(description="Human-readable description")
    category: str = Field(description="Tool category")
    permissions_required: List[str] = Field(default_factory=list, description="Required permissions")
    input_schema: Dict[str, Any] = Field(description="JSON schema for inputs")
    output_schema: Optional[Dict[str, Any]] = Field(default=None, description="JSON schema for outputs")
    handler: Optional[Callable] = Field(default=None, exclude=True, description="Execution handler")
    version: str = Field(default="1.0.0", description="Tool version")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Business requirements (can override permission defaults)
    plan_tiers: Optional[List[str]] = Field(default=None, description="Required plan tiers")
    feature_flags: Optional[List[str]] = Field(default=None, description="Required feature flags")
    rate_limits: Optional[Dict[str, int]] = Field(default=None, description="Custom rate limits")
    
    # Metadata
    examples: Optional[List[Dict[str, Any]]] = Field(default=None, description="Usage examples")
    documentation_url: Optional[str] = Field(default=None, description="Documentation URL")
    deprecated: bool = Field(default=False, description="Is tool deprecated")
    experimental: bool = Field(default=False, description="Is tool experimental")


class ToolExecutionResult(BaseModel):
    """Result of tool execution"""
    tool_name: str
    user_id: str
    status: str  # "success", "error", "permission_denied", "rate_limited"
    result: Optional[Any] = None
    error_message: Optional[str] = None
    execution_time_ms: int = 0
    permission_check: Optional[PermissionCheckResult] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class UnifiedToolRegistry:
    """
    Unified registry for all tools across the platform
    
    Replaces:
    - AdminToolRegistry
    - MCP ToolRegistry  
    - Individual tool collections
    """
    
    def __init__(self, permission_service: ToolPermissionService):
        self.tools: Dict[str, UnifiedTool] = {}
        self.permission_service = permission_service
        self.execution_log: List[ToolExecutionResult] = []
        self._initialize_builtin_tools()
    
    def _initialize_builtin_tools(self):
        """Initialize all built-in tools"""
        self._register_basic_tools()
        self._register_analytics_tools()
        self._register_data_management_tools()
        self._register_optimization_tools()
        self._register_system_management_tools()
        self._register_developer_tools()
    
    def _register_basic_tools(self):
        """Register basic user tools"""
        self.register_tool(UnifiedTool(
            name="create_thread",
            description="Create a new conversation thread",
            category="Thread Management",
            permissions_required=["basic"],
            input_schema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Thread title"},
                    "metadata": {"type": "object", "description": "Thread metadata"}
                }
            },
            handler=self._create_thread_handler,
        ))
        
        self.register_tool(UnifiedTool(
            name="get_thread_history",
            description="Get message history for a thread",
            category="Thread Management",
            permissions_required=["basic"],
            input_schema={
                "type": "object",
                "properties": {
                    "thread_id": {"type": "string", "description": "Thread ID"},
                    "limit": {"type": "integer", "description": "Message limit", "default": 50}
                },
                "required": ["thread_id"]
            },
            handler=self._get_thread_history_handler,
        ))
        
        self.register_tool(UnifiedTool(
            name="list_agents",
            description="List available agents",
            category="Agent Operations",
            permissions_required=["basic"],
            input_schema={
                "type": "object",
                "properties": {
                    "category": {"type": "string", "description": "Filter by category"}
                }
            },
            handler=self._list_agents_handler,
        ))
    
    def _register_analytics_tools(self):
        """Register analytics tools"""
        self.register_tool(UnifiedTool(
            name="analyze_workload",
            description="Analyze AI workload characteristics",
            category="Analytics",
            permissions_required=["analytics"],
            input_schema={
                "type": "object",
                "properties": {
                    "workload_data": {"type": "object", "description": "Workload data"},
                    "metrics": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["workload_data"]
            },
            handler=self._analyze_workload_handler,
        ))
        
        self.register_tool(UnifiedTool(
            name="query_corpus",
            description="Search document corpus",
            category="Analytics",
            permissions_required=["analytics"],
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "limit": {"type": "integer", "default": 10},
                    "filters": {"type": "object"}
                },
                "required": ["query"]
            },
            handler=self._query_corpus_handler,
        ))
    
    def _register_data_management_tools(self):
        """Register data management tools"""
        self.register_tool(UnifiedTool(
            name="generate_synthetic_data",
            description="Generate synthetic test data",
            category="Data Management",
            permissions_required=["data_management"],
            input_schema={
                "type": "object",
                "properties": {
                    "schema": {"type": "object", "description": "Data schema"},
                    "count": {"type": "integer", "default": 10},
                    "format": {"type": "string", "enum": ["json", "csv"], "default": "json"}
                },
                "required": ["schema"]
            },
            handler=self._generate_synthetic_data_handler,
        ))
        
        self.register_tool(UnifiedTool(
            name="corpus_manager",
            description="Create and manage document corpora",
            category="Data Management",
            permissions_required=["data_management"],
            input_schema={
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["create", "update", "delete", "list"]},
                    "corpus_data": {"type": "object", "description": "Corpus configuration"}
                },
                "required": ["action"]
            },
            handler=self._corpus_manager_handler,
        ))
    
    def _register_optimization_tools(self):
        """Register advanced optimization tools"""
        optimization_tools = [
            "cost_analyzer", "latency_analyzer", "performance_predictor",
            "multi_objective_optimization", "kv_cache_optimization_audit"
        ]
        
        for tool_name in optimization_tools:
            self.register_tool(UnifiedTool(
                name=tool_name,
                description=f"Advanced {tool_name.replace('_', ' ')} tool",
                category="Advanced Optimization",
                permissions_required=["advanced_optimization"],
                input_schema={
                    "type": "object",
                    "properties": {
                        "data": {"type": "object", "description": "Analysis data"},
                        "options": {"type": "object", "description": "Tool options"}
                    },
                    "required": ["data"]
                },
                handler=getattr(self, f"_{tool_name}_handler", self._generic_optimization_handler),
            ))
    
    def _register_system_management_tools(self):
        """Register system management tools"""
        self.register_tool(UnifiedTool(
            name="system_configurator",
            description="Configure system settings",
            category="System Management",
            permissions_required=["system_management"],
            input_schema={
                "type": "object",
                "properties": {
                    "setting_name": {"type": "string"},
                    "value": {"description": "Setting value"},
                    "action": {"type": "string", "enum": ["get", "set", "list"]}
                },
                "required": ["action"]
            },
            handler=self._system_configurator_handler,
        ))
        
        self.register_tool(UnifiedTool(
            name="user_admin",
            description="User management operations",
            category="System Management", 
            permissions_required=["system_management"],
            input_schema={
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["create", "update", "delete", "list"]},
                    "user_data": {"type": "object"}
                },
                "required": ["action"]
            },
            handler=self._user_admin_handler,
        ))
        
        self.register_tool(UnifiedTool(
            name="log_analyzer",
            description="Analyze system logs",
            category="System Management",
            permissions_required=["system_management"],
            input_schema={
                "type": "object", 
                "properties": {
                    "query": {"type": "string", "description": "Log query"},
                    "time_range": {"type": "string", "default": "1h"}
                }
            },
            handler=self._log_analyzer_handler,
        ))
    
    def _register_developer_tools(self):
        """Register developer tools"""
        self.register_tool(UnifiedTool(
            name="debug_panel",
            description="Access debug information",
            category="Developer Tools",
            permissions_required=["developer_tools"],
            input_schema={
                "type": "object",
                "properties": {
                    "component": {"type": "string", "description": "Component to debug"},
                    "action": {"type": "string", "enum": ["status", "logs", "metrics"]}
                }
            },
            handler=self._debug_panel_handler,
        ))
    
    def register_tool(self, tool: UnifiedTool):
        """Register a new tool"""
        if tool.name in self.tools:
            logger.warning(f"Overwriting existing tool: {tool.name}")
        
        self.tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name} (category: {tool.category})")
    
    def unregister_tool(self, tool_name: str):
        """Unregister a tool"""
        if tool_name in self.tools:
            del self.tools[tool_name]
            logger.info(f"Unregistered tool: {tool_name}")
    
    async def list_available_tools(
        self, 
        user: User, 
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List tools available to a specific user"""
        try:
            # Create execution context for permission checking
            context = ToolExecutionContext(
                user_id=str(user.id),
                tool_name="",  # Will be set per tool
                requested_action="list",
                user_plan=getattr(user, 'plan_tier', 'free'),
                user_roles=getattr(user, 'roles', []),
                feature_flags=getattr(user, 'feature_flags', {}),
                is_developer=getattr(user, 'is_developer', False),
            )
            
            available_tools = []
            
            for tool_name, tool in self.tools.items():
                # Filter by category if specified
                if category and tool.category.lower() != category.lower():
                    continue
                
                # Check if tool is deprecated
                if tool.deprecated:
                    continue
                
                # Check permissions
                context.tool_name = tool_name
                permission_result = await self.permission_service.check_tool_permission(context)
                
                tool_info = {
                    "name": tool.name,
                    "description": tool.description,
                    "category": tool.category,
                    "available": permission_result.allowed,
                    "version": tool.version,
                    "experimental": tool.experimental,
                }
                
                # Add permission info if not available
                if not permission_result.allowed:
                    tool_info.update({
                        "reason": permission_result.reason,
                        "required_permissions": permission_result.required_permissions,
                        "upgrade_path": permission_result.upgrade_path,
                    })
                
                # Add input schema for available tools
                if permission_result.allowed:
                    tool_info["input_schema"] = tool.input_schema
                
                available_tools.append(tool_info)
            
            return available_tools
            
        except Exception as e:
            logger.error(f"Error listing available tools: {e}", exc_info=True)
            return []
    
    async def execute_tool(
        self, 
        tool_name: str, 
        arguments: Dict[str, Any],
        user: User
    ) -> ToolExecutionResult:
        """Execute a tool with permission checking"""
        start_time = datetime.utcnow()
        
        # Create execution context
        context = ToolExecutionContext(
            user_id=str(user.id),
            tool_name=tool_name,
            requested_action="execute",
            user_plan=getattr(user, 'plan_tier', 'free'),
            user_roles=getattr(user, 'roles', []),
            feature_flags=getattr(user, 'feature_flags', {}),
            is_developer=getattr(user, 'is_developer', False),
        )
        
        try:
            # Check if tool exists
            if tool_name not in self.tools:
                return ToolExecutionResult(
                    tool_name=tool_name,
                    user_id=str(user.id),
                    status="error",
                    error_message=f"Tool '{tool_name}' not found",
                    execution_time_ms=0
                )
            
            tool = self.tools[tool_name]
            
            # Check permissions
            permission_result = await self.permission_service.check_tool_permission(context)
            
            if not permission_result.allowed:
                return ToolExecutionResult(
                    tool_name=tool_name,
                    user_id=str(user.id),
                    status="permission_denied",
                    error_message=permission_result.reason,
                    permission_check=permission_result,
                    execution_time_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000)
                )
            
            # Validate input schema (basic validation)
            # TODO: Implement JSON schema validation
            
            # Execute tool handler
            if not tool.handler:
                return ToolExecutionResult(
                    tool_name=tool_name,
                    user_id=str(user.id),
                    status="error",
                    error_message=f"Tool '{tool_name}' has no handler",
                    execution_time_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000)
                )
            
            # Execute handler (async or sync)
            if inspect.iscoroutinefunction(tool.handler):
                result = await tool.handler(arguments, user)
            else:
                result = tool.handler(arguments, user)
            
            execution_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            # Record usage for rate limiting
            await self.permission_service.record_tool_usage(
                user_id=str(user.id),
                tool_name=tool_name,
                execution_time_ms=execution_time_ms,
                status="success"
            )
            
            execution_result = ToolExecutionResult(
                tool_name=tool_name,
                user_id=str(user.id),
                status="success",
                result=result,
                permission_check=permission_result,
                execution_time_ms=execution_time_ms
            )
            
            self.execution_log.append(execution_result)
            return execution_result
            
        except Exception as e:
            execution_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            logger.error(f"Tool execution failed: {tool_name} - {e}", exc_info=True)
            
            # Record usage even for failed executions
            await self.permission_service.record_tool_usage(
                user_id=str(user.id),
                tool_name=tool_name,
                execution_time_ms=execution_time_ms,
                status="error"
            )
            
            return ToolExecutionResult(
                tool_name=tool_name,
                user_id=str(user.id),
                status="error",
                error_message=str(e),
                execution_time_ms=execution_time_ms
            )
    
    def get_tool_categories(self) -> List[Dict[str, Any]]:
        """Get list of tool categories"""
        categories = {}
        
        for tool in self.tools.values():
            if tool.category not in categories:
                categories[tool.category] = {
                    "name": tool.category,
                    "tools": [],
                    "count": 0
                }
            
            categories[tool.category]["tools"].append(tool.name)
            categories[tool.category]["count"] += 1
        
        return list(categories.values())
    
    # Tool Handlers (these would be implemented based on existing functionality)
    
    async def _create_thread_handler(self, arguments: Dict[str, Any], user: User):
        """Handler for create_thread tool"""
        # TODO: Implement actual thread creation
        return {
            "type": "text",
            "text": f"Created thread: {arguments.get('title', 'Untitled')}",
            "thread_id": "placeholder_thread_id"
        }
    
    async def _get_thread_history_handler(self, arguments: Dict[str, Any], user: User):
        """Handler for get_thread_history tool"""
        # TODO: Implement actual thread history retrieval
        return {
            "type": "text", 
            "text": f"Thread history for {arguments['thread_id']}"
        }
    
    async def _list_agents_handler(self, arguments: Dict[str, Any], user: User):
        """Handler for list_agents tool"""
        # TODO: Get actual agent list
        return {
            "type": "text",
            "text": "Available agents: TriageSubAgent, DataSubAgent, OptimizationsCoreSubAgent"
        }
    
    async def _analyze_workload_handler(self, arguments: Dict[str, Any], user: User):
        """Handler for analyze_workload tool"""
        # TODO: Implement actual workload analysis
        return {
            "type": "text",
            "text": "Workload analysis complete"
        }
    
    async def _query_corpus_handler(self, arguments: Dict[str, Any], user: User):
        """Handler for query_corpus tool"""
        # TODO: Implement actual corpus query
        return {
            "type": "text",
            "text": f"Corpus search results for: {arguments['query']}"
        }
    
    async def _generate_synthetic_data_handler(self, arguments: Dict[str, Any], user: User):
        """Handler for generate_synthetic_data tool"""
        # TODO: Implement actual synthetic data generation
        return {
            "type": "text",
            "text": f"Generated {arguments.get('count', 10)} synthetic records"
        }
    
    async def _corpus_manager_handler(self, arguments: Dict[str, Any], user: User):
        """Handler for corpus_manager tool"""
        # TODO: Implement actual corpus management
        return {
            "type": "text",
            "text": f"Corpus {arguments['action']} completed"
        }
    
    async def _generic_optimization_handler(self, arguments: Dict[str, Any], user: User):
        """Generic handler for optimization tools"""
        # TODO: Implement actual optimization logic
        return {
            "type": "text",
            "text": "Optimization analysis completed"
        }
    
    async def _system_configurator_handler(self, arguments: Dict[str, Any], user: User):
        """Handler for system_configurator tool"""
        # TODO: Implement actual system configuration
        return {
            "type": "text", 
            "text": f"System configuration {arguments['action']} completed"
        }
    
    async def _user_admin_handler(self, arguments: Dict[str, Any], user: User):
        """Handler for user_admin tool"""
        # TODO: Implement actual user administration
        return {
            "type": "text",
            "text": f"User {arguments['action']} completed"
        }
    
    async def _log_analyzer_handler(self, arguments: Dict[str, Any], user: User):
        """Handler for log_analyzer tool"""
        # TODO: Implement actual log analysis
        return {
            "type": "text",
            "text": f"Log analysis completed for query: {arguments.get('query', '')}"
        }
    
    async def _debug_panel_handler(self, arguments: Dict[str, Any], user: User):
        """Handler for debug_panel tool"""
        # TODO: Implement actual debug panel
        return {
            "type": "text",
            "text": f"Debug info for {arguments.get('component', 'system')}"
        }