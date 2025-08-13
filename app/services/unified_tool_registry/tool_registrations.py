"""
Tool Registration Utilities

Contains methods for registering different categories of tools with the unified registry.
"""
from typing import TYPE_CHECKING
from .models import UnifiedTool

if TYPE_CHECKING:
    from .registry import UnifiedToolRegistry


class ToolRegistrationMixin:
    """Mixin containing tool registration methods"""
    
    def _register_basic_tools(self: "UnifiedToolRegistry"):
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
    
    def _register_analytics_tools(self: "UnifiedToolRegistry"):
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
    
    def _register_data_management_tools(self: "UnifiedToolRegistry"):
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
    
    def _register_optimization_tools(self: "UnifiedToolRegistry"):
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
    
    def _register_system_management_tools(self: "UnifiedToolRegistry"):
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
    
    def _register_developer_tools(self: "UnifiedToolRegistry"):
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