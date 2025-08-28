"""Permission Definitions Module - Tool permission definitions and loading"""

from typing import Dict

from netra_backend.app.schemas.tool_permission import (
    BusinessRequirement,
    PermissionLevel,
    RateLimit,
    ToolPermission,
)


class PermissionDefinitions:
    """Handles loading and managing permission definitions"""

    @staticmethod
    def load_permission_definitions() -> Dict[str, ToolPermission]:
        """Load tool permission definitions"""
        return {
            "basic": PermissionDefinitions._load_basic_permission(),
            "analytics": PermissionDefinitions._load_analytics_permission(),
            "data_management": PermissionDefinitions._load_data_management_permission(),
            "advanced_optimization": PermissionDefinitions._load_advanced_optimization_permission(),
            "system_management": PermissionDefinitions._load_system_management_permission(),
            "developer_tools": PermissionDefinitions._load_developer_tools_permission()
        }
    
    @staticmethod
    def _load_basic_permission() -> ToolPermission:
        """Load basic user permission definition"""
        return ToolPermission(
            name="basic", description="Basic authenticated user tools",
            level=PermissionLevel.READ,
            tools=["create_thread", "get_thread_history", "list_agents", "get_agent_status"],
            business_requirements=BusinessRequirement()
        )
    
    @staticmethod
    def _load_analytics_permission() -> ToolPermission:
        """Load analytics permission definition"""
        return ToolPermission(
            name="analytics", description="Workload analytics and basic optimization",
            level=PermissionLevel.READ, tools=["analyze_workload", "query_corpus", "optimize_prompt"],
            business_requirements=BusinessRequirement(plan_tiers=["pro", "enterprise"]),
            rate_limits=RateLimit(per_hour=100, per_day=1000)
        )
    
    @staticmethod
    def _load_data_management_permission() -> ToolPermission:
        """Load data management permission definition"""
        return ToolPermission(
            name="data_management", description="Data operations and corpus management",
            level=PermissionLevel.WRITE, tools=["generate_synthetic_data", "corpus_manager", "create_corpus", "modify_corpus"],
            business_requirements=BusinessRequirement(plan_tiers=["pro", "enterprise"], feature_flags=["data_operations"]),
            rate_limits=RateLimit(per_hour=50, per_day=500)
        )
    
    @staticmethod
    def _load_advanced_optimization_permission() -> ToolPermission:
        """Load advanced optimization permission definition"""
        tools = ["cost_analyzer", "latency_analyzer", "performance_predictor", "multi_objective_optimization", "kv_cache_optimization_audit", "advanced_optimization_for_core_function"]
        return ToolPermission(
            name="advanced_optimization", description="Advanced AI optimization tools",
            level=PermissionLevel.WRITE, tools=tools,
            business_requirements=BusinessRequirement(plan_tiers=["enterprise"], feature_flags=["advanced_optimization"]),
            rate_limits=RateLimit(per_hour=20, per_day=100))
    
    @staticmethod
    def _load_system_management_permission() -> ToolPermission:
        """Load system management permission definition"""
        return ToolPermission(
            name="system_management", description="System configuration and management",
            level=PermissionLevel.ADMIN, tools=["system_configurator", "log_analyzer", "user_admin", "feature_flag_toggle"],
            business_requirements=BusinessRequirement(plan_tiers=["enterprise"], role_requirements=["admin", "developer"])
        )
    
    @staticmethod
    def _load_developer_tools_permission() -> ToolPermission:
        """Load developer tools permission definition"""
        return ToolPermission(
            name="developer_tools", description="Development and debugging tools",
            level=PermissionLevel.ADMIN, tools=["debug_panel", "impersonation_tool", "system_logs", "database_query_tool"],
            business_requirements=BusinessRequirement(developer_status=True, environment=["development", "staging"])
        )