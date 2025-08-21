# Tool Permission Definitions Module
from typing import Dict
from netra_backend.app.schemas.ToolPermission import (
    ToolPermission, PermissionLevel, BusinessRequirement, RateLimit
)

class PermissionDefinitions:
    """Manages tool permission definitions."""
    
    @staticmethod
    def get_all() -> Dict[str, ToolPermission]:
        """Get all permission definitions."""
        definitions = {}
        definitions.update(PermissionDefinitions._get_basic())
        definitions.update(PermissionDefinitions._get_analytics())
        definitions.update(PermissionDefinitions._get_data_management())
        definitions.update(PermissionDefinitions._get_advanced())
        definitions.update(PermissionDefinitions._get_system())
        return definitions
    
    @staticmethod
    def _get_basic() -> Dict[str, ToolPermission]:
        """Get basic permission definitions."""
        return {
            "basic": ToolPermission(
                name="basic",
                description="Basic authenticated user tools",
                level=PermissionLevel.READ,
                tools=[
                    "create_thread", "get_thread_history",
                    "list_agents", "get_agent_status"
                ],
                business_requirements=BusinessRequirement(),
            )
        }
    
    @staticmethod
    def _get_analytics() -> Dict[str, ToolPermission]:
        """Get analytics permission definitions."""
        return {
            "analytics": ToolPermission(
                name="analytics",
                description="Workload analytics and basic optimization",
                level=PermissionLevel.READ,
                tools=[
                    "analyze_workload", "query_corpus", "optimize_prompt"
                ],
                business_requirements=BusinessRequirement(
                    plan_tiers=["pro", "enterprise"],
                ),
                rate_limits=RateLimit(per_hour=100, per_day=1000),
            )
        }
    
    @staticmethod
    def _get_data_management() -> Dict[str, ToolPermission]:
        """Get data management permission definitions."""
        return {
            "data_management": ToolPermission(
                name="data_management",
                description="Data operations and corpus management",
                level=PermissionLevel.WRITE,
                tools=[
                    "generate_synthetic_data", "corpus_manager",
                    "create_corpus", "modify_corpus"
                ],
                business_requirements=BusinessRequirement(
                    plan_tiers=["pro", "enterprise"],
                    feature_flags=["data_operations"],
                ),
                rate_limits=RateLimit(per_hour=50, per_day=500),
            )
        }
    
    @staticmethod
    def _get_advanced() -> Dict[str, ToolPermission]:
        """Get advanced optimization permission definitions."""
        return {
            "advanced_optimization": ToolPermission(
                name="advanced_optimization",
                description="Advanced AI optimization tools",
                level=PermissionLevel.WRITE,
                tools=[
                    "cost_analyzer", "latency_analyzer",
                    "performance_predictor", "multi_objective_optimization",
                    "kv_cache_optimization_audit",
                    "advanced_optimization_for_core_function"
                ],
                business_requirements=BusinessRequirement(
                    plan_tiers=["enterprise"],
                    feature_flags=["advanced_optimization"],
                ),
                rate_limits=RateLimit(per_hour=20, per_day=100),
            )
        }
    
    @staticmethod
    def _get_system() -> Dict[str, ToolPermission]:
        """Get system management permission definitions."""
        return {
            "system_management": ToolPermission(
                name="system_management",
                description="System configuration and management",
                level=PermissionLevel.ADMIN,
                tools=[
                    "system_configurator", "log_analyzer",
                    "user_admin", "feature_flag_toggle"
                ],
                business_requirements=BusinessRequirement(
                    plan_tiers=["enterprise"],
                    role_requirements=["admin", "developer"],
                ),
            ),
            "monitoring": ToolPermission(
                name="monitoring",
                description="System monitoring and health checks",
                level=PermissionLevel.READ,
                tools=[
                    "system_health", "get_metrics", "view_logs"
                ],
                business_requirements=BusinessRequirement(
                    plan_tiers=["pro", "enterprise"],
                ),
            )
        }