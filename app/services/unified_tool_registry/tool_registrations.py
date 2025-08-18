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
        self._register_create_thread_tool()
        self._register_get_thread_history_tool()
        self._register_list_agents_tool()

    def _register_create_thread_tool(self: "UnifiedToolRegistry") -> None:
        """Register create thread tool."""
        tool = self._create_create_thread_tool()
        self.register_tool(tool)

    def _register_get_thread_history_tool(self: "UnifiedToolRegistry") -> None:
        """Register get thread history tool."""
        tool = self._create_get_thread_history_tool()
        self.register_tool(tool)

    def _register_list_agents_tool(self: "UnifiedToolRegistry") -> None:
        """Register list agents tool."""
        tool = self._create_list_agents_tool()
        self.register_tool(tool)

    def _create_create_thread_tool(self: "UnifiedToolRegistry") -> UnifiedTool:
        """Create create thread tool definition."""
        return UnifiedTool(
            name="create_thread",
            description="Create a new conversation thread",
            category="Thread Management",
            permissions_required=["basic"],
            input_schema=self._get_create_thread_schema(),
            handler=self._create_thread_handler,
        )

    def _create_get_thread_history_tool(self: "UnifiedToolRegistry") -> UnifiedTool:
        """Create get thread history tool definition."""
        return UnifiedTool(
            name="get_thread_history",
            description="Get message history for a thread",
            category="Thread Management",
            permissions_required=["basic"],
            input_schema=self._get_thread_history_schema(),
            handler=self._get_thread_history_handler,
        )

    def _create_list_agents_tool(self: "UnifiedToolRegistry") -> UnifiedTool:
        """Create list agents tool definition."""
        return UnifiedTool(
            name="list_agents",
            description="List available agents",
            category="Agent Operations",
            permissions_required=["basic"],
            input_schema=self._get_list_agents_schema(),
            handler=self._list_agents_handler,
        )

    def _get_create_thread_schema(self) -> dict:
        """Get create thread tool schema."""
        return {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Thread title"},
                "metadata": {"type": "object", "description": "Thread metadata"}
            }
        }

    def _get_thread_history_schema(self) -> dict:
        """Get thread history tool schema."""
        return {
            "type": "object",
            "properties": {
                "thread_id": {"type": "string", "description": "Thread ID"},
                "limit": {"type": "integer", "description": "Message limit", "default": 50}
            },
            "required": ["thread_id"]
        }

    def _get_list_agents_schema(self) -> dict:
        """Get list agents tool schema."""
        return {
            "type": "object",
            "properties": {
                "category": {"type": "string", "description": "Filter by category"}
            }
        }
    
    def _register_analytics_tools(self: "UnifiedToolRegistry"):
        """Register analytics tools"""
        self._register_analyze_workload_tool()
        self._register_query_corpus_tool()

    def _register_analyze_workload_tool(self: "UnifiedToolRegistry") -> None:
        """Register analyze workload tool."""
        tool = self._create_analyze_workload_tool()
        self.register_tool(tool)

    def _register_query_corpus_tool(self: "UnifiedToolRegistry") -> None:
        """Register query corpus tool."""
        tool = self._create_query_corpus_tool()
        self.register_tool(tool)

    def _create_analyze_workload_tool(self: "UnifiedToolRegistry") -> UnifiedTool:
        """Create analyze workload tool definition."""
        return UnifiedTool(
            name="analyze_workload",
            description="Analyze AI workload characteristics",
            category="Analytics",
            permissions_required=["analytics"],
            input_schema=self._get_analyze_workload_schema(),
            handler=self._analyze_workload_handler,
        )

    def _create_query_corpus_tool(self: "UnifiedToolRegistry") -> UnifiedTool:
        """Create query corpus tool definition."""
        return UnifiedTool(
            name="query_corpus",
            description="Search document corpus",
            category="Analytics",
            permissions_required=["analytics"],
            input_schema=self._get_query_corpus_schema(),
            handler=self._query_corpus_handler,
        )

    def _get_analyze_workload_schema(self) -> dict:
        """Get analyze workload tool schema."""
        return {
            "type": "object",
            "properties": {
                "workload_data": {"type": "object", "description": "Workload data"},
                "metrics": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["workload_data"]
        }

    def _get_query_corpus_schema(self) -> dict:
        """Get query corpus tool schema."""
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "limit": {"type": "integer", "default": 10},
                "filters": {"type": "object"}
            },
            "required": ["query"]
        }
    
    def _register_data_management_tools(self: "UnifiedToolRegistry"):
        """Register data management tools"""
        self._register_synthetic_data_tool()
        self._register_corpus_manager_tool()

    def _register_synthetic_data_tool(self: "UnifiedToolRegistry") -> None:
        """Register synthetic data tool."""
        tool = self._create_synthetic_data_tool()
        self.register_tool(tool)

    def _register_corpus_manager_tool(self: "UnifiedToolRegistry") -> None:
        """Register corpus manager tool."""
        tool = self._create_corpus_manager_tool()
        self.register_tool(tool)

    def _create_synthetic_data_tool(self: "UnifiedToolRegistry") -> UnifiedTool:
        """Create synthetic data tool definition."""
        return UnifiedTool(
            name="generate_synthetic_data",
            description="Generate synthetic test data",
            category="Data Management",
            permissions_required=["data_management"],
            input_schema=self._get_synthetic_data_schema(),
            handler=self._generate_synthetic_data_handler,
        )

    def _create_corpus_manager_tool(self: "UnifiedToolRegistry") -> UnifiedTool:
        """Create corpus manager tool definition."""
        return UnifiedTool(
            name="corpus_manager",
            description="Create and manage document corpora",
            category="Data Management",
            permissions_required=["data_management"],
            input_schema=self._get_corpus_manager_schema(),
            handler=self._corpus_manager_handler,
        )

    def _get_synthetic_data_schema(self) -> dict:
        """Get synthetic data tool schema."""
        return {
            "type": "object",
            "properties": {
                "schema": {"type": "object", "description": "Data schema"},
                "count": {"type": "integer", "default": 10},
                "format": {"type": "string", "enum": ["json", "csv"], "default": "json"}
            },
            "required": ["schema"]
        }

    def _get_corpus_manager_schema(self) -> dict:
        """Get corpus manager tool schema."""
        return {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["create", "update", "delete", "list"]},
                "corpus_data": {"type": "object", "description": "Corpus configuration"}
            },
            "required": ["action"]
        }
    
    def _register_optimization_tools(self: "UnifiedToolRegistry"):
        """Register advanced optimization tools"""
        optimization_tools = self._get_optimization_tool_names()
        for tool_name in optimization_tools:
            self._register_single_optimization_tool(tool_name)

    def _get_optimization_tool_names(self) -> list[str]:
        """Get list of optimization tool names."""
        return [
            "cost_analyzer", "latency_analyzer", "performance_predictor",
            "multi_objective_optimization", "kv_cache_optimization_audit"
        ]

    def _register_single_optimization_tool(self: "UnifiedToolRegistry", tool_name: str) -> None:
        """Register a single optimization tool."""
        tool = self._create_optimization_tool(tool_name)
        self.register_tool(tool)

    def _create_optimization_tool(self: "UnifiedToolRegistry", tool_name: str) -> UnifiedTool:
        """Create optimization tool definition."""
        return UnifiedTool(
            name=tool_name,
            description=f"Advanced {tool_name.replace('_', ' ')} tool",
            category="Advanced Optimization",
            permissions_required=["advanced_optimization"],
            input_schema=self._get_optimization_tool_schema(),
            handler=getattr(self, f"_{tool_name}_handler", self._generic_optimization_handler),
        )

    def _get_optimization_tool_schema(self) -> dict:
        """Get optimization tool schema."""
        return {
            "type": "object",
            "properties": {
                "data": {"type": "object", "description": "Analysis data"},
                "options": {"type": "object", "description": "Tool options"}
            },
            "required": ["data"]
        }
    
    def _register_system_management_tools(self: "UnifiedToolRegistry"):
        """Register system management tools"""
        self._register_system_configurator()
        self._register_user_admin()
        self._register_log_analyzer()
    
    def _register_system_configurator(self: "UnifiedToolRegistry"):
        """Register system configurator tool"""
        tool = self._create_system_configurator_tool()
        self.register_tool(tool)
    
    def _register_user_admin(self: "UnifiedToolRegistry"):
        """Register user admin tool"""
        tool = self._create_user_admin_tool()
        self.register_tool(tool)
    
    def _register_log_analyzer(self: "UnifiedToolRegistry"):
        """Register log analyzer tool"""
        tool = self._create_log_analyzer_tool()
        self.register_tool(tool)
    
    def _create_system_configurator_tool(self: "UnifiedToolRegistry") -> UnifiedTool:
        """Create system configurator tool definition"""
        return UnifiedTool(
            name="system_configurator",
            description="Configure system settings",
            category="System Management",
            permissions_required=["system_management"],
            input_schema=self._get_system_configurator_schema(),
            handler=self._system_configurator_handler,
        )
    
    def _create_user_admin_tool(self: "UnifiedToolRegistry") -> UnifiedTool:
        """Create user admin tool definition"""
        return UnifiedTool(
            name="user_admin",
            description="User management operations",
            category="System Management", 
            permissions_required=["system_management"],
            input_schema=self._get_user_admin_schema(),
            handler=self._user_admin_handler,
        )
    
    def _create_log_analyzer_tool(self: "UnifiedToolRegistry") -> UnifiedTool:
        """Create log analyzer tool definition"""
        return UnifiedTool(
            name="log_analyzer",
            description="Analyze system logs",
            category="System Management",
            permissions_required=["system_management"],
            input_schema=self._get_log_analyzer_schema(),
            handler=self._log_analyzer_handler,
        )
    
    def _get_system_configurator_schema(self) -> dict:
        """Get system configurator input schema"""
        return {
            "type": "object",
            "properties": {
                "setting_name": {"type": "string"},
                "value": {"description": "Setting value"},
                "action": {"type": "string", "enum": ["get", "set", "list"]}
            },
            "required": ["action"]
        }
    
    def _get_user_admin_schema(self) -> dict:
        """Get user admin input schema"""
        return {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["create", "update", "delete", "list"]},
                "user_data": {"type": "object"}
            },
            "required": ["action"]
        }
    
    def _get_log_analyzer_schema(self) -> dict:
        """Get log analyzer input schema"""
        return {
            "type": "object", 
            "properties": {
                "query": {"type": "string", "description": "Log query"},
                "time_range": {"type": "string", "default": "1h"}
            }
        }
    
    def _register_developer_tools(self: "UnifiedToolRegistry"):
        """Register developer tools"""
        tool = self._create_debug_panel_tool()
        self.register_tool(tool)

    def _create_debug_panel_tool(self: "UnifiedToolRegistry") -> UnifiedTool:
        """Create debug panel tool definition."""
        return UnifiedTool(
            name="debug_panel",
            description="Access debug information",
            category="Developer Tools",
            permissions_required=["developer_tools"],
            input_schema=self._get_debug_panel_schema(),
            handler=self._debug_panel_handler,
        )

    def _get_debug_panel_schema(self) -> dict:
        """Get debug panel tool schema."""
        return {
            "type": "object",
            "properties": {
                "component": {"type": "string", "description": "Component to debug"},
                "action": {"type": "string", "enum": ["status", "logs", "metrics"]}
            }
        }