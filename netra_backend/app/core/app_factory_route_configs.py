"""Route configuration utilities for FastAPI application factory."""


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
        "auth_proxy": (modules["auth_proxy_router"], "", ["auth"])
        # auth_resilience router removed - functionality consolidated into auth_client_core
    }


def _get_api_route_configs(modules: dict) -> dict:
    """Get API route configurations."""
    return {"threads": (modules["threads_router"], "", ["threads"]),
        "llm_cache": (modules["llm_cache_router"], "/api/llm-cache", ["llm-cache"]),
        "mcp": (modules["mcp_router"], "/api/mcp", ["mcp"])}


def _get_service_route_configs(modules: dict) -> dict:
    """Get service route configurations."""
    return {"quality": (modules["quality"].router, "", ["quality"]),
        "websocket": (modules["websocket_router"], "", ["websocket"]),
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
    return {"admin": (modules["admin"].router, "/api", ["admin"]),
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
            "users": (modules["users"].router, "", ["users"])}


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


def get_all_route_configurations(modules: dict) -> dict:
    """Get complete route configuration mapping."""
    core_configs = get_core_route_configs(modules)
    business_configs = get_business_route_configs(modules)
    utility_configs = get_utility_route_configs(modules)
    return {**core_configs, **business_configs, **utility_configs}