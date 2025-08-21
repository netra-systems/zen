"""
Tool Registration Utilities

Contains methods for registering different categories of tools with the unified registry.
"""
from typing import TYPE_CHECKING
from netra_backend.app.services.unified_tool_registry.models import UnifiedTool

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
        config = self._get_create_thread_config()
        return self._build_unified_tool(*config)

    def _create_get_thread_history_tool(self: "UnifiedToolRegistry") -> UnifiedTool:
        """Create get thread history tool definition."""
        config = self._get_thread_history_config()
        return self._build_unified_tool(*config)

    def _create_list_agents_tool(self: "UnifiedToolRegistry") -> UnifiedTool:
        """Create list agents tool definition."""
        config = self._get_list_agents_config()
        return self._build_unified_tool(*config)

    def _get_create_thread_schema(self) -> dict:
        """Get create thread tool schema."""
        return self._build_schema(
            {
                "title": {"type": "string", "description": "Thread title"},
                "metadata": {"type": "object", "description": "Thread metadata"}
            }
        )

    def _get_thread_history_schema(self) -> dict:
        """Get thread history tool schema."""
        properties = self._get_thread_history_properties()
        return self._build_schema_with_required(
            properties,
            ["thread_id"]
        )

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
        config = self._get_analyze_workload_config()
        return self._build_unified_tool(*config)

    def _create_query_corpus_tool(self: "UnifiedToolRegistry") -> UnifiedTool:
        """Create query corpus tool definition."""
        config = self._get_query_corpus_config()
        return self._build_unified_tool(*config)

    def _get_analyze_workload_schema(self) -> dict:
        """Get analyze workload tool schema."""
        properties = self._get_workload_analysis_properties()
        return self._build_schema_with_required(
            properties,
            ["workload_data"]
        )

    def _get_query_corpus_schema(self) -> dict:
        """Get query corpus tool schema."""
        properties = self._get_corpus_query_properties()
        return self._build_schema_with_required(
            properties,
            ["query"]
        )
    
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
        config = self._get_synthetic_data_config()
        return self._build_unified_tool(*config)

    def _create_corpus_manager_tool(self: "UnifiedToolRegistry") -> UnifiedTool:
        """Create corpus manager tool definition."""
        config = self._get_corpus_manager_config()
        return self._build_unified_tool(*config)

    def _get_synthetic_data_schema(self) -> dict:
        """Get synthetic data tool schema."""
        properties = self._get_synthetic_data_properties()
        return self._build_schema_with_required(
            properties,
            ["schema"]
        )

    def _get_corpus_manager_schema(self) -> dict:
        """Get corpus manager tool schema."""
        properties = self._get_corpus_manager_properties()
        return self._build_schema_with_required(
            properties,
            ["action"]
        )
    
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
        config = self._get_optimization_tool_config(tool_name)
        return self._build_unified_tool(*config)

    def _get_optimization_tool_schema(self) -> dict:
        """Get optimization tool schema."""
        properties = self._get_optimization_properties()
        return self._build_schema_with_required(
            properties,
            ["data"]
        )
    
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
        config = self._get_system_configurator_config()
        return self._build_unified_tool(*config)
    
    def _create_user_admin_tool(self: "UnifiedToolRegistry") -> UnifiedTool:
        """Create user admin tool definition"""
        config = self._get_user_admin_config()
        return self._build_unified_tool(*config)
    
    def _create_log_analyzer_tool(self: "UnifiedToolRegistry") -> UnifiedTool:
        """Create log analyzer tool definition"""
        config = self._get_log_analyzer_config()
        return self._build_unified_tool(*config)
    
    def _get_system_configurator_schema(self) -> dict:
        """Get system configurator input schema"""
        properties = self._get_system_configurator_properties()
        return self._build_schema_with_required(
            properties,
            ["action"]
        )
    
    def _get_user_admin_schema(self) -> dict:
        """Get user admin input schema"""
        properties = self._get_user_admin_properties()
        return self._build_schema_with_required(
            properties,
            ["action"]
        )
    
    def _get_log_analyzer_schema(self) -> dict:
        """Get log analyzer input schema"""
        properties = self._get_log_analyzer_properties()
        return self._build_schema(properties)
    
    def _register_developer_tools(self: "UnifiedToolRegistry"):
        """Register developer tools"""
        tool = self._create_debug_panel_tool()
        self.register_tool(tool)

    def _create_debug_panel_tool(self: "UnifiedToolRegistry") -> UnifiedTool:
        """Create debug panel tool definition."""
        config = self._get_debug_panel_config()
        return self._build_unified_tool(*config)

    def _get_debug_panel_schema(self) -> dict:
        """Get debug panel tool schema."""
        properties = self._get_debug_panel_properties()
        return self._build_schema(properties)
    
    def _build_unified_tool(self, name: str, description: str, category: str, 
                           permissions: list, schema: dict, handler) -> UnifiedTool:
        """Build unified tool with standard parameters."""
        return UnifiedTool(
            name=name, description=description, category=category,
            permissions_required=permissions, input_schema=schema, handler=handler
        )
    
    def _build_schema(self, properties: dict) -> dict:
        """Build basic schema with properties."""
        return {
            "type": "object",
            "properties": properties
        }
    
    def _build_schema_with_required(self, properties: dict, required: list) -> dict:
        """Build schema with properties and required fields."""
        return {
            "type": "object",
            "properties": properties,
            "required": required
        }
    
    def _get_thread_history_properties(self) -> dict:
        """Get thread history schema properties."""
        return {
            "thread_id": {"type": "string", "description": "Thread ID"},
            "limit": {"type": "integer", "description": "Message limit", "default": 50}
        }
    
    def _get_workload_analysis_properties(self) -> dict:
        """Get workload analysis schema properties."""
        return {
            "workload_data": {"type": "object", "description": "Workload data"},
            "metrics": {"type": "array", "items": {"type": "string"}}
        }
    
    def _get_corpus_query_properties(self) -> dict:
        """Get corpus query schema properties."""
        return {
            "query": {"type": "string", "description": "Search query"},
            "limit": {"type": "integer", "default": 10},
            "filters": {"type": "object"}
        }
    
    def _get_synthetic_data_properties(self) -> dict:
        """Get synthetic data schema properties."""
        return {
            "schema": {"type": "object", "description": "Data schema"},
            "count": {"type": "integer", "default": 10},
            "format": {"type": "string", "enum": ["json", "csv"], "default": "json"}
        }
    
    def _get_corpus_manager_properties(self) -> dict:
        """Get corpus manager schema properties."""
        return {
            "action": {"type": "string", "enum": ["create", "update", "delete", "list"]},
            "corpus_data": {"type": "object", "description": "Corpus configuration"}
        }
    
    def _get_optimization_properties(self) -> dict:
        """Get optimization tool schema properties."""
        return {
            "data": {"type": "object", "description": "Analysis data"},
            "options": {"type": "object", "description": "Tool options"}
        }
    
    def _get_system_configurator_properties(self) -> dict:
        """Get system configurator schema properties."""
        return {
            "setting_name": {"type": "string"},
            "value": {"description": "Setting value"},
            "action": {"type": "string", "enum": ["get", "set", "list"]}
        }
    
    def _get_user_admin_properties(self) -> dict:
        """Get user admin schema properties."""
        return {
            "action": {"type": "string", "enum": ["create", "update", "delete", "list"]},
            "user_data": {"type": "object"}
        }
    
    def _get_log_analyzer_properties(self) -> dict:
        """Get log analyzer schema properties."""
        return {
            "query": {"type": "string", "description": "Log query"},
            "time_range": {"type": "string", "default": "1h"}
        }
    
    def _get_debug_panel_properties(self) -> dict:
        """Get debug panel schema properties."""
        return {
            "component": {"type": "string", "description": "Component to debug"},
            "action": {"type": "string", "enum": ["status", "logs", "metrics"]}
        }
    
    def _get_create_thread_config(self) -> tuple:
        """Get create thread tool configuration."""
        return (
            "create_thread", "Create a new conversation thread",
            "Thread Management", ["basic"], self._get_create_thread_schema(),
            self._create_thread_handler
        )
    
    def _get_thread_history_config(self) -> tuple:
        """Get thread history tool configuration."""
        return (
            "get_thread_history", "Get message history for a thread",
            "Thread Management", ["basic"], self._get_thread_history_schema(),
            self._get_thread_history_handler
        )
    
    def _get_list_agents_config(self) -> tuple:
        """Get list agents tool configuration."""
        return (
            "list_agents", "List available agents", "Agent Operations",
            ["basic"], self._get_list_agents_schema(), self._list_agents_handler
        )
    
    def _get_analyze_workload_config(self) -> tuple:
        """Get analyze workload tool configuration."""
        return (
            "analyze_workload", "Analyze AI workload characteristics",
            "Analytics", ["analytics"], self._get_analyze_workload_schema(),
            self._analyze_workload_handler
        )
    
    def _get_query_corpus_config(self) -> tuple:
        """Get query corpus tool configuration."""
        return (
            "query_corpus", "Search document corpus", "Analytics",
            ["analytics"], self._get_query_corpus_schema(), self._query_corpus_handler
        )
    
    def _get_synthetic_data_config(self) -> tuple:
        """Get synthetic data tool configuration."""
        return (
            "generate_synthetic_data", "Generate synthetic test data",
            "Data Management", ["data_management"], self._get_synthetic_data_schema(),
            self._generate_synthetic_data_handler
        )
    
    def _get_corpus_manager_config(self) -> tuple:
        """Get corpus manager tool configuration."""
        return (
            "corpus_manager", "Create and manage document corpora",
            "Data Management", ["data_management"], self._get_corpus_manager_schema(),
            self._corpus_manager_handler
        )
    
    def _get_optimization_tool_config(self, tool_name: str) -> tuple:
        """Get optimization tool configuration."""
        description = f"Advanced {tool_name.replace('_', ' ')} tool"
        handler = getattr(self, f"_{tool_name}_handler", self._generic_optimization_handler)
        return (
            tool_name, description, "Advanced Optimization", ["advanced_optimization"],
            self._get_optimization_tool_schema(), handler
        )
    
    def _get_system_configurator_config(self) -> tuple:
        """Get system configurator tool configuration."""
        return (
            "system_configurator", "Configure system settings", "System Management",
            ["system_management"], self._get_system_configurator_schema(),
            self._system_configurator_handler
        )
    
    def _get_user_admin_config(self) -> tuple:
        """Get user admin tool configuration."""
        return (
            "user_admin", "User management operations", "System Management",
            ["system_management"], self._get_user_admin_schema(), self._user_admin_handler
        )
    
    def _get_log_analyzer_config(self) -> tuple:
        """Get log analyzer tool configuration."""
        return (
            "log_analyzer", "Analyze system logs", "System Management",
            ["system_management"], self._get_log_analyzer_schema(), self._log_analyzer_handler
        )
    
    def _get_debug_panel_config(self) -> tuple:
        """Get debug panel tool configuration."""
        return (
            "debug_panel", "Access debug information", "Developer Tools",
            ["developer_tools"], self._get_debug_panel_schema(), self._debug_panel_handler
        )