"""
Unified Tool Registry - Central registry for all tools with permission-based access
"""
from typing import Dict, List, Optional, Any, Callable, Union
from datetime import datetime, UTC
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
        start_time = datetime.now(UTC)
        
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
                    execution_time_ms=int((datetime.now(UTC) - start_time).total_seconds() * 1000)
                )
            
            # Validate input schema (basic validation)
            # Implement JSON schema validation
            if tool_def.input_schema:
                from jsonschema import validate, ValidationError
                try:
                    validate(instance=arguments, schema=tool_def.input_schema)
                except ValidationError as ve:
                    raise NetraException(f"Invalid input: {ve.message}")
            
            # Execute tool handler
            if not tool.handler:
                return ToolExecutionResult(
                    tool_name=tool_name,
                    user_id=str(user.id),
                    status="error",
                    error_message=f"Tool '{tool_name}' has no handler",
                    execution_time_ms=int((datetime.now(UTC) - start_time).total_seconds() * 1000)
                )
            
            # Execute handler (async or sync)
            if inspect.iscoroutinefunction(tool.handler):
                result = await tool.handler(arguments, user)
            else:
                result = tool.handler(arguments, user)
            
            execution_time_ms = int((datetime.now(UTC) - start_time).total_seconds() * 1000)
            
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
            execution_time_ms = int((datetime.now(UTC) - start_time).total_seconds() * 1000)
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
        from app.services.thread_service import ThreadService
        
        thread_service = ThreadService(self.db)
        
        thread = await thread_service.create_thread(
            user_id=user.id,
            title=arguments.get('title', 'Untitled'),
            initial_message=arguments.get('initial_message'),
            metadata=arguments.get('metadata', {})
        )
        
        return {
            "type": "text",
            "text": f"Created thread: {thread.title}",
            "thread_id": thread.id,
            "created_at": thread.created_at.isoformat()
        }
    
    async def _get_thread_history_handler(self, arguments: Dict[str, Any], user: User):
        """Handler for get_thread_history tool"""
        from app.services.thread_service import ThreadService
        
        thread_service = ThreadService(self.db)
        
        history = await thread_service.get_thread_history(
            thread_id=arguments['thread_id'],
            user_id=user.id,
            limit=arguments.get('limit', 50)
        )
        
        return {
            "type": "text", 
            "text": f"Thread history for {arguments['thread_id']}",
            "messages": history.get('messages', []),
            "total_count": history.get('total_count', 0)
        }
    
    async def _list_agents_handler(self, arguments: Dict[str, Any], user: User):
        """Handler for list_agents tool"""
        from app.agents.supervisor import SupervisorAgent
        
        supervisor = SupervisorAgent(self.db)
        agents = supervisor.get_registered_agents()
        
        agent_list = []
        for name, agent_class in agents.items():
            agent_list.append({
                "name": name,
                "type": agent_class.__name__,
                "capabilities": getattr(agent_class, 'capabilities', [])
            })
        
        return {
            "type": "text",
            "text": f"Available agents ({len(agent_list)}): " + ", ".join([a['name'] for a in agent_list]),
            "agents": agent_list
        }
    
    async def _analyze_workload_handler(self, arguments: Dict[str, Any], user: User):
        """Handler for analyze_workload tool"""
        from app.services.apex_optimizer_service import ApexOptimizerService
        
        optimizer = ApexOptimizerService(self.db)
        
        analysis = await optimizer.analyze_workload({
            "workload_type": arguments.get('workload_type', 'general'),
            "metrics": arguments.get('metrics', {}),
            "user_id": user.id
        })
        
        recommendations = await optimizer.generate_recommendations(analysis)
        
        return {
            "type": "text",
            "text": "Workload analysis complete",
            "analysis": analysis,
            "recommendations": recommendations
        }
    
    async def _query_corpus_handler(self, arguments: Dict[str, Any], user: User):
        """Handler for query_corpus tool"""
        from app.services.corpus_service import CorpusService
        
        corpus_service = CorpusService(self.db)
        
        results = await corpus_service.search(
            query=arguments['query'],
            filters=arguments.get('filters', {}),
            limit=arguments.get('limit', 10),
            user_id=user.id
        )
        
        return {
            "type": "text",
            "text": f"Found {len(results)} results for: {arguments['query']}",
            "results": results
        }
    
    async def _generate_synthetic_data_handler(self, arguments: Dict[str, Any], user: User):
        """Handler for generate_synthetic_data tool"""
        from app.services.synthetic_data_service import SyntheticDataService
        
        synthetic_service = SyntheticDataService(self.db)
        
        data = await synthetic_service.generate(
            data_type=arguments.get('data_type', 'generic'),
            count=arguments.get('count', 10),
            schema=arguments.get('schema', {}),
            user_id=user.id
        )
        
        return {
            "type": "text",
            "text": f"Generated {len(data)} synthetic records",
            "data": data
        }
    
    async def _corpus_manager_handler(self, arguments: Dict[str, Any], user: User):
        """Handler for corpus_manager tool"""
        from app.services.corpus_service import CorpusService
        
        corpus_service = CorpusService(self.db)
        action = arguments['action']
        
        if action == 'create':
            corpus = await corpus_service.create_corpus(
                name=arguments['name'],
                description=arguments.get('description'),
                user_id=user.id
            )
            return {
                "type": "text",
                "text": f"Created corpus: {corpus.name}",
                "corpus_id": corpus.id
            }
        elif action == 'delete':
            await corpus_service.delete_corpus(
                corpus_id=arguments['corpus_id'],
                user_id=user.id
            )
            return {
                "type": "text",
                "text": f"Deleted corpus: {arguments['corpus_id']}"
            }
        elif action == 'list':
            corpora = await corpus_service.list_corpora(user_id=user.id)
            return {
                "type": "text",
                "text": f"Found {len(corpora)} corpora",
                "corpora": corpora
            }
        else:
            return {
                "type": "text",
                "text": f"Unknown action: {action}"
            }
    
    async def _generic_optimization_handler(self, arguments: Dict[str, Any], user: User):
        """Generic handler for optimization tools"""
        from app.services.apex_optimizer_service import ApexOptimizerService
        
        optimizer = ApexOptimizerService(self.db)
        
        optimization_type = arguments.get('type', 'general')
        target_metrics = arguments.get('target_metrics', {})
        
        result = await optimizer.optimize(
            optimization_type=optimization_type,
            target_metrics=target_metrics,
            constraints=arguments.get('constraints', {}),
            user_id=user.id
        )
        
        return {
            "type": "text",
            "text": f"{optimization_type} optimization completed",
            "result": result,
            "improvements": result.get('improvements', {})
        }
    
    async def _system_configurator_handler(self, arguments: Dict[str, Any], user: User):
        """Handler for system_configurator tool"""
        from app.services.configuration_service import ConfigurationService
        
        config_service = ConfigurationService(self.db)
        action = arguments['action']
        
        if action == 'get':
            config = await config_service.get_configuration(
                key=arguments['key'],
                user_id=user.id
            )
            return {
                "type": "text", 
                "text": f"Retrieved configuration: {arguments['key']}",
                "config": config
            }
        elif action == 'set':
            await config_service.set_configuration(
                key=arguments['key'],
                value=arguments['value'],
                user_id=user.id
            )
            return {
                "type": "text", 
                "text": f"Updated configuration: {arguments['key']}"
            }
        elif action == 'reset':
            await config_service.reset_configuration(
                key=arguments.get('key'),
                user_id=user.id
            )
            return {
                "type": "text", 
                "text": "Configuration reset completed"
            }
        else:
            return {
                "type": "text",
                "text": f"Unknown action: {action}"
            }
    
    async def _user_admin_handler(self, arguments: Dict[str, Any], user: User):
        """Handler for user_admin tool"""
        from app.services.user_service import UserService
        
        # Check admin permissions
        if not user.is_admin:
            return {
                "type": "text",
                "text": "Admin privileges required",
                "error": True
            }
        
        user_service = UserService(self.db)
        action = arguments['action']
        
        if action == 'create':
            new_user = await user_service.create_user(
                email=arguments['email'],
                username=arguments.get('username'),
                role=arguments.get('role', 'user')
            )
            return {
                "type": "text",
                "text": f"Created user: {new_user.email}",
                "user_id": new_user.id
            }
        elif action == 'update':
            await user_service.update_user(
                user_id=arguments['user_id'],
                updates=arguments.get('updates', {})
            )
            return {
                "type": "text",
                "text": f"Updated user: {arguments['user_id']}"
            }
        elif action == 'delete':
            await user_service.delete_user(user_id=arguments['user_id'])
            return {
                "type": "text",
                "text": f"Deleted user: {arguments['user_id']}"
            }
        elif action == 'list':
            users = await user_service.list_users(
                filters=arguments.get('filters', {})
            )
            return {
                "type": "text",
                "text": f"Found {len(users)} users",
                "users": users
            }
        else:
            return {
                "type": "text",
                "text": f"Unknown action: {action}"
            }
    
    async def _log_analyzer_handler(self, arguments: Dict[str, Any], user: User):
        """Handler for log_analyzer tool"""
        from app.services.log_analysis_service import LogAnalysisService
        
        log_service = LogAnalysisService(self.db)
        
        analysis = await log_service.analyze_logs(
            query=arguments.get('query', ''),
            time_range=arguments.get('time_range', '1h'),
            log_level=arguments.get('log_level'),
            service=arguments.get('service'),
            user_id=user.id
        )
        
        return {
            "type": "text",
            "text": f"Log analysis completed",
            "analysis": analysis,
            "total_logs": analysis.get('total_count', 0),
            "error_count": analysis.get('error_count', 0),
            "warning_count": analysis.get('warning_count', 0)
        }
    
    async def _debug_panel_handler(self, arguments: Dict[str, Any], user: User):
        """Handler for debug_panel tool"""
        from app.services.debug_service import DebugService
        
        debug_service = DebugService(self.db)
        component = arguments.get('component', 'system')
        
        debug_info = await debug_service.get_debug_info(
            component=component,
            include_metrics=arguments.get('include_metrics', True),
            include_logs=arguments.get('include_logs', False),
            user_id=user.id
        )
        
        return {
            "type": "text",
            "text": f"Debug info for {component}",
            "debug_info": debug_info,
            "timestamp": debug_info.get('timestamp'),
            "health_status": debug_info.get('health_status', 'unknown')
        }