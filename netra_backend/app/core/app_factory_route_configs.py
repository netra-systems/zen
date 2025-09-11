"""Route configuration utilities for FastAPI application factory.

CRITICAL: All route prefixes MUST be managed here centrally.
Individual routers should NOT define their own prefixes in APIRouter() initialization.
See SPEC/learnings/router_double_prefix_pattern.xml for details.
"""


def get_core_route_configs(modules: dict) -> dict:
    """Get core API route configurations."""
    auth_configs = _get_auth_route_configs(modules)
    api_configs = _get_api_route_configs(modules)
    service_configs = _get_service_route_configs(modules)
    return {**auth_configs, **api_configs, **service_configs}


def _get_auth_route_configs(modules: dict) -> dict:
    """Get authentication route configurations."""
    # Auth proxy router added for backward compatibility with tests
    return {
        "agent": (modules["agent_router"], "/api/agent", ["agent"]),
        "auth_proxy": (modules["auth_proxy_router"], "", ["auth"]),
        "auth_compat": (modules["auth_compat_router"], "", ["auth-compat"]),
        "agents_execute": (modules["agents_execute_router"], "/api/agents", ["agents"]),
        "metrics_api": (modules["metrics_api_router"], "/api/metrics", ["metrics"]),
        "health_check": (modules["health_check_router"], "/api/health", ["health-check"]),
        "system_info": (modules["system_info_router"], "/api/system", ["system-info"])
        # auth_resilience router removed - functionality consolidated into auth_client_core
        # health_check and system_info routers added - provides system introspection
    }


def _get_api_route_configs(modules: dict) -> dict:
    """Get API route configurations."""
    return {"threads": (modules["threads_router"], "", ["threads"]),
        "messages": (modules["messages_router"], "/api/chat", ["messages"]),
        "messages_root": (modules["messages_root_router"], "/api/messages", ["messages-root"]),
        "llm_cache": (modules["llm_cache_router"], "/api/llm-cache", ["llm-cache"]),
        "mcp": (modules["mcp_router"], "/api/mcp", ["mcp"]),
        "events_stream": (modules["events_stream_router"], "/api/events", ["events"])}


def _get_service_route_configs(modules: dict) -> dict:
    """Get service route configurations."""
    return {"quality": (modules["quality"].router, "", ["quality"]),
        "websocket": (modules["websocket_router"], "", ["websocket"]),
        "websocket_isolated": (modules["websocket_isolated_router"], "", ["websocket-isolated"]),
        "discovery": (modules["discovery"].router, "", ["discovery"])}


def get_business_route_configs(modules: dict) -> dict:
    """Get business logic route configurations."""
    core_business = _get_core_business_configs(modules)
    extended_business = _get_extended_business_configs(modules)
    return {**core_business, **extended_business}


def _get_core_business_configs(modules: dict) -> dict:
    """Get core business route configurations."""
    supply_configs = _get_supply_business_configs(modules)
    admin_configs = _get_admin_business_configs(modules)
    return {**supply_configs, **admin_configs}


def _get_supply_business_configs(modules: dict) -> dict:
    """Get supply and generation business route configurations."""
    return {"supply": (modules["supply"].router, "/api/supply", ["supply"]),
            "generation": (modules["generation"].router, "/api/generation", ["generation"])}


def _get_admin_business_configs(modules: dict) -> dict:
    """Get admin and references business route configurations."""
    return {"admin": (modules["admin"].router, "/api/admin", ["admin"]),
            "references": (modules["references"].router, "/api", ["references"])}


def _get_extended_business_configs(modules: dict) -> dict:
    """Get extended business route configurations."""
    health_configs = _get_health_business_configs(modules)
    monitoring_configs = _get_monitoring_business_configs(modules)
    return {**health_configs, **monitoring_configs}


def _get_health_business_configs(modules: dict) -> dict:
    """Get health-related business route configurations."""
    return {"health": (modules["health"].router, "/health", ["health"]),
            "health_extended": (modules["health_extended_router"], "", ["monitoring"])}


def _get_monitoring_business_configs(modules: dict) -> dict:
    """Get monitoring and corpus business route configurations."""
    return {"monitoring": (modules["monitoring_router"], "/api", ["database-monitoring"]),
            "gcp_monitoring": (modules["gcp_monitoring_router"], "/api", ["gcp-error-monitoring"]),
            "circuit_breaker": (modules["circuit_breaker_router"], "", ["circuit-breaker-monitoring"]),
            "corpus": (modules["corpus"].router, "/api/corpus", ["corpus"])}


def get_utility_route_configs(modules: dict) -> dict:
    """Get utility and factory route configurations."""
    utility_configs = _get_utility_configs(modules)
    factory_configs = _get_factory_configs(modules)
    return {**utility_configs, **factory_configs}


def _get_utility_configs(modules: dict) -> dict:
    """Get utility route configurations."""
    data_configs = _get_data_utility_configs(modules)
    tool_configs = _get_tool_utility_configs(modules)
    return {**data_configs, **tool_configs}


def _get_data_utility_configs(modules: dict) -> dict:
    """Get data utility route configurations."""
    return {"synthetic_data": (modules["synthetic_data"].router, "", ["synthetic_data"]),
            "config": (modules["config"].router, "/api", ["config"])}


def _get_tool_utility_configs(modules: dict) -> dict:
    """Get tool utility route configurations."""
    return {"demo": (modules["demo"].router, "", ["demo"]),
            "unified_tools": (modules["unified_tools"].router, "/api/tools", ["unified-tools"]),
            "users": (modules["users"].router, "/api/v1", ["users"])}


def _get_factory_configs(modules: dict) -> dict:
    """Get factory route configurations."""
    status_configs = _get_factory_status_configs(modules)
    analyzer_configs = _get_factory_analyzer_configs(modules)
    return {**status_configs, **analyzer_configs}


def _get_factory_status_configs(modules: dict) -> dict:
    """Get factory status route configurations."""
    return {"factory_status": (modules["factory_status_router"], "", ["factory-status"]),
            "factory_status_simple": (modules["factory_status_simple_router"], "", ["factory-status-simple"])}


def _get_factory_analyzer_configs(modules: dict) -> dict:
    """Get factory analyzer route configurations."""
    return {"factory_compliance": (modules["factory_compliance_router"], "", ["factory-compliance"]),
            "github_analyzer": (modules["github_analyzer_router"], "", ["github-analyzer"])}


def get_test_route_configs(modules: dict) -> dict:
    """Get test route configurations for development environment."""
    configs = {}
    
    if "test_router" in modules:
        configs["test"] = (modules["test_router"], "", ["test"])
    
    if "test_gcp_errors_router" in modules:
        configs["test_gcp_errors"] = (modules["test_gcp_errors_router"], "", ["test-gcp-errors"])
    
    return configs


def get_all_route_configurations(modules: dict) -> dict:
    """Get complete route configuration mapping."""
    core_configs = get_core_route_configs(modules)
    business_configs = get_business_route_configs(modules)
    utility_configs = get_utility_route_configs(modules)
    test_configs = get_test_route_configs(modules)
    return {**core_configs, **business_configs, **utility_configs, **test_configs}