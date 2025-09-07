from shared.isolated_environment import get_env
"""Route module imports for FastAPI application factory."""

def import_basic_route_modules() -> dict:
    """Import basic route modules."""
    route_imports = _import_core_routes()
    return _create_basic_modules_dict_from_imports(route_imports)


def _import_core_routes() -> tuple:
    """Import core route modules as tuple."""
    from netra_backend.app.routes import (
        admin,
        config,
        corpus,
        demo,
        discovery,
        generation,
        health,
        quality,
        references,
        supply,
        synthetic_data,
        unified_tools,
        users,
    )
    return (supply, generation, admin, references, health, corpus,
            synthetic_data, config, demo, unified_tools, quality, users, discovery)


def _create_basic_modules_dict_from_imports(imports: tuple) -> dict:
    """Create basic modules dict from imported tuple."""
    unpacked = _unpack_route_imports(imports)
    return _create_basic_modules_dict(*unpacked)


def _unpack_route_imports(imports: tuple) -> tuple:
    """Unpack route imports tuple."""
    return imports


def _create_basic_modules_dict(supply, generation, admin, references, health, corpus, synthetic_data, config, demo, unified_tools, quality, users, discovery) -> dict:
    """Create basic modules dictionary mapping"""
    core_modules = _create_core_modules_dict(supply, generation, admin, references)
    extended_modules = _create_extended_modules_dict(health, corpus, synthetic_data, config)
    utility_modules = _create_utility_modules_dict(demo, unified_tools, quality, users)
    system_modules = _create_system_modules_dict(discovery)
    return {**core_modules, **extended_modules, **utility_modules, **system_modules}


def _create_core_modules_dict(supply, generation, admin, references) -> dict:
    """Create core modules dictionary mapping."""
    return {"supply": supply, "generation": generation, "admin": admin, "references": references}


def _create_extended_modules_dict(health, corpus, synthetic_data, config) -> dict:
    """Create extended modules dictionary mapping."""
    return {"health": health, "corpus": corpus, "synthetic_data": synthetic_data, "config": config}


def _create_utility_modules_dict(demo, unified_tools, quality, users) -> dict:
    """Create utility modules dictionary mapping."""
    return {"demo": demo, "unified_tools": unified_tools, "quality": quality, "users": users}


def _create_system_modules_dict(discovery) -> dict:
    """Create system modules dictionary mapping."""
    return {"discovery": discovery}


def import_named_routers() -> dict:
    """Import named router modules."""
    auth_routers = _import_auth_routers()
    core_routers = _import_core_routers()
    extended_routers = _import_extended_routers()
    return {**auth_routers, **core_routers, **extended_routers}


def _import_auth_routers() -> dict:
    """Import authentication-related routers"""
    from netra_backend.app.routes.agent_route import router as agent_router
    from netra_backend.app.routes.auth_proxy import router as auth_proxy_router
    from netra_backend.app.routes.auth_proxy import compat_router as auth_compat_router
    from netra_backend.app.routes.agents_execute import router as agents_execute_router
    from netra_backend.app.routes.metrics_api import router as metrics_api_router
    from netra_backend.app.routes.health_check import router as health_check_router
    from netra_backend.app.routes.system_info import router as system_info_router
    # Auth resilience router removed - functionality consolidated into auth_client_core
    # Auth proxy router added - provides backward compatibility for tests
    # Agent execution router added - provides E2E test endpoints
    # Health check and system info routers added - provides system introspection
    return {
        "agent_router": agent_router, 
        "auth_proxy_router": auth_proxy_router,
        "auth_compat_router": auth_compat_router,
        "agents_execute_router": agents_execute_router,
        "metrics_api_router": metrics_api_router,
        "health_check_router": health_check_router,
        "system_info_router": system_info_router
    }


def _import_core_routers() -> dict:
    """Import core functionality routers"""
    from netra_backend.app.routes.llm_cache import router as llm_cache_router
    from netra_backend.app.routes.mcp import router as mcp_router
    from netra_backend.app.routes.threads_route import router as threads_router
    from netra_backend.app.routes.messages import router as messages_router
    return {"llm_cache_router": llm_cache_router, "threads_router": threads_router, "mcp_router": mcp_router, "messages_router": messages_router}


def _import_extended_routers() -> dict:
    """Import extended functionality routers"""
    extended_imports = _import_extended_router_modules()
    test_routers = _import_test_routers()
    return {**_create_extended_router_dict(extended_imports), **test_routers}


def _import_extended_router_modules() -> tuple:
    """Import extended router modules as tuple."""
    from netra_backend.app.routes.gcp_monitoring import router as gcp_monitoring_router
    from netra_backend.app.routes.health_extended import (
        router as health_extended_router,
    )
    from netra_backend.app.routes.monitoring import router as monitoring_router
    from netra_backend.app.routes.websocket import (
        router as websocket_router,
    )
    from netra_backend.app.routes.websocket_isolated import (
        router as websocket_isolated_router,
    )
    return health_extended_router, monitoring_router, gcp_monitoring_router, websocket_router, websocket_isolated_router


def _create_extended_router_dict(router_imports: tuple) -> dict:
    """Create extended router dictionary from imports."""
    health_extended_router, monitoring_router, gcp_monitoring_router, websocket_router, websocket_isolated_router = router_imports
    return {"health_extended_router": health_extended_router,
        "monitoring_router": monitoring_router, "gcp_monitoring_router": gcp_monitoring_router,
        "websocket_router": websocket_router, "websocket_isolated_router": websocket_isolated_router}


def _import_test_routers() -> dict:
    """Import test routers for development environment."""
    import os
    # Only import in development environment
    environment = get_env().get("ENVIRONMENT", "development").lower()
    if environment in ["development", "staging", "testing"]:
        routers = {}
        
        # Import existing test endpoints
        try:
            from netra_backend.app.api.test_endpoints import router as test_router
            routers["test_router"] = test_router
        except ImportError:
            pass
        
        # Import GCP error test endpoints
        try:
            from netra_backend.app.routes.test_gcp_errors import router as test_gcp_errors_router
            routers["test_gcp_errors_router"] = test_gcp_errors_router
        except ImportError:
            pass
        
        return routers
    return {}


def import_factory_routers() -> dict:
    """Import factory and analyzer router modules."""
    status_routers = _import_factory_status_routers()
    analyzer_routers = _import_factory_analyzer_routers()
    return {**status_routers, **analyzer_routers}


def _import_factory_status_routers() -> dict:
    """Import factory status router modules."""
    from netra_backend.app.routes.factory_status import router as factory_status_router
    from netra_backend.app.routes.factory_status_simple import (
        router as factory_status_simple_router,
    )
    return {"factory_status_router": factory_status_router,
            "factory_status_simple_router": factory_status_simple_router}


def _import_factory_analyzer_routers() -> dict:
    """Import factory analyzer router modules."""
    from netra_backend.app.routes.factory_compliance import (
        router as factory_compliance_router,
    )
    from netra_backend.app.routes.github_analyzer import (
        router as github_analyzer_router,
    )
    return {"factory_compliance_router": factory_compliance_router,
            "github_analyzer_router": github_analyzer_router}


def import_all_route_modules() -> dict:
    """Import all route modules."""
    basic_modules = import_basic_route_modules()
    named_routers = import_named_routers()
    factory_routers = import_factory_routers()
    return {**basic_modules, **named_routers, **factory_routers}
