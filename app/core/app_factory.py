"""
FastAPI application factory module.
Handles application creation, router registration, and middleware setup.
"""
from fastapi import FastAPI
from pydantic import ValidationError
from fastapi import HTTPException

from app.core.lifespan_manager import lifespan
from app.core.middleware_setup import (
    setup_cors_middleware, 
    create_cors_redirect_middleware,
    setup_session_middleware
)
from app.core.request_context import (
    create_error_context_middleware,
    create_request_logging_middleware
)
from app.core.exceptions_base import NetraException
from app.core.error_handlers import (
    netra_exception_handler,
    validation_exception_handler,
    http_exception_handler,
    general_exception_handler,
)
# OAuth now handled by auth service


def create_fastapi_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(lifespan=lifespan)
    return app


# Startup and shutdown events now handled by lifespan manager


def register_error_handlers(app: FastAPI) -> None:
    """Register application error handlers."""
    app.add_exception_handler(NetraException, netra_exception_handler)
    app.add_exception_handler(ValidationError, validation_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)


def _setup_security_middleware(app: FastAPI) -> None:
    """Setup security middleware components."""
    _add_ip_blocking_middleware(app)
    _add_path_traversal_middleware(app)
    _add_security_headers_middleware(app)


def _add_ip_blocking_middleware(app: FastAPI) -> None:
    """Add IP blocking middleware."""
    from app.middleware.ip_blocking import ip_blocking_middleware
    app.middleware("http")(ip_blocking_middleware)


def _add_path_traversal_middleware(app: FastAPI) -> None:
    """Add path traversal protection middleware."""
    from app.middleware.path_traversal_protection import path_traversal_protection_middleware
    app.middleware("http")(path_traversal_protection_middleware)


def _add_security_headers_middleware(app: FastAPI) -> None:
    """Add security headers middleware."""
    from app.middleware.security_headers import SecurityHeadersMiddleware
    from app.config import settings
    app.add_middleware(SecurityHeadersMiddleware, environment=settings.environment)


def _setup_request_middleware(app: FastAPI) -> None:
    """Setup CORS, error, and request logging middleware."""
    setup_cors_middleware(app)
    app.middleware("http")(create_cors_redirect_middleware())
    app.middleware("http")(create_error_context_middleware())
    app.middleware("http")(create_request_logging_middleware())
    setup_session_middleware(app)


def setup_middleware(app: FastAPI) -> None:
    """Setup all middleware for the application."""
    _setup_security_middleware(app)
    _setup_request_middleware(app)


def initialize_oauth(app: FastAPI) -> None:
    """Initialize OAuth client."""
    # OAuth now handled by auth service - no initialization needed
    pass


def register_api_routes(app: FastAPI) -> None:
    """Register all API routes."""
    _import_and_register_routes(app)


def _import_and_register_routes(app: FastAPI) -> None:
    """Import and register all route modules."""
    route_modules = _import_route_modules()
    route_configs = _get_route_configurations(route_modules)
    _register_route_modules(app, route_configs)


def _import_basic_route_modules() -> dict:
    """Import basic route modules."""
    route_imports = _import_core_routes()
    return _create_basic_modules_dict_from_imports(route_imports)


def _import_core_routes() -> tuple:
    """Import core route modules as tuple."""
    from app.routes import (supply, generation, admin, references, health, 
        corpus, synthetic_data, config, demo, unified_tools, quality)
    return (supply, generation, admin, references, health, corpus,
            synthetic_data, config, demo, unified_tools, quality)


def _create_basic_modules_dict_from_imports(imports: tuple) -> dict:
    """Create basic modules dict from imported tuple."""
    supply, generation, admin, references, health, corpus, synthetic_data, config, demo, unified_tools, quality = imports
    return _create_basic_modules_dict(
        supply, generation, admin, references, health, corpus,
        synthetic_data, config, demo, unified_tools, quality
    )

def _create_basic_modules_dict(supply, generation, admin, references, health, corpus, synthetic_data, config, demo, unified_tools, quality) -> dict:
    """Create basic modules dictionary mapping"""
    core_modules = _create_core_modules_dict(supply, generation, admin, references)
    extended_modules = _create_extended_modules_dict(health, corpus, synthetic_data, config)
    utility_modules = _create_utility_modules_dict(demo, unified_tools, quality)
    return {**core_modules, **extended_modules, **utility_modules}

def _create_core_modules_dict(supply, generation, admin, references) -> dict:
    """Create core modules dictionary mapping."""
    return {"supply": supply, "generation": generation, "admin": admin, "references": references}

def _create_extended_modules_dict(health, corpus, synthetic_data, config) -> dict:
    """Create extended modules dictionary mapping."""
    return {"health": health, "corpus": corpus, "synthetic_data": synthetic_data, "config": config}

def _create_utility_modules_dict(demo, unified_tools, quality) -> dict:
    """Create utility modules dictionary mapping."""
    return {"demo": demo, "unified_tools": unified_tools, "quality": quality}


def _import_named_routers() -> dict:
    """Import named router modules."""
    auth_routers = _import_auth_routers()
    core_routers = _import_core_routers()
    extended_routers = _import_extended_routers()
    return {**auth_routers, **core_routers, **extended_routers}

def _import_auth_routers() -> dict:
    """Import authentication-related routers"""
    from app.routes.auth import router as auth_router
    from app.routes.agent_route import router as agent_router
    return {"auth_router": auth_router, "agent_router": agent_router}

def _import_core_routers() -> dict:
    """Import core functionality routers"""
    from app.routes.llm_cache import router as llm_cache_router
    from app.routes.threads_route import router as threads_router
    return {"llm_cache_router": llm_cache_router, "threads_router": threads_router}

def _import_extended_routers() -> dict:
    """Import extended functionality routers"""
    extended_imports = _import_extended_router_modules()
    return _create_extended_router_dict(extended_imports)

def _import_extended_router_modules() -> tuple:
    """Import extended router modules as tuple."""
    from app.routes.health_extended import router as health_extended_router
    from app.routes.monitoring import router as monitoring_router
    from app.routes.websockets import router as websockets_router
    return health_extended_router, monitoring_router, websockets_router

def _create_extended_router_dict(router_imports: tuple) -> dict:
    """Create extended router dictionary from imports."""
    health_extended_router, monitoring_router, websockets_router = router_imports
    return {"health_extended_router": health_extended_router,
        "monitoring_router": monitoring_router, "websockets_router": websockets_router}


def _import_factory_routers() -> dict:
    """Import factory and analyzer router modules."""
    status_routers = _import_factory_status_routers()
    analyzer_routers = _import_factory_analyzer_routers()
    return {**status_routers, **analyzer_routers}


def _import_factory_status_routers() -> dict:
    """Import factory status router modules."""
    from app.routes.factory_status import router as factory_status_router
    from app.routes.factory_status_simple import router as factory_status_simple_router
    return {"factory_status_router": factory_status_router,
            "factory_status_simple_router": factory_status_simple_router}


def _import_factory_analyzer_routers() -> dict:
    """Import factory analyzer router modules."""
    from app.routes.factory_compliance import router as factory_compliance_router
    from app.routes.github_analyzer import router as github_analyzer_router
    return {"factory_compliance_router": factory_compliance_router,
            "github_analyzer_router": github_analyzer_router}


def _import_route_modules() -> dict:
    """Import all route modules."""
    basic_modules = _import_basic_route_modules()
    named_routers = _import_named_routers()
    factory_routers = _import_factory_routers()
    return {**basic_modules, **named_routers, **factory_routers}


def _get_core_route_configs(modules: dict) -> dict:
    """Get core API route configurations."""
    auth_configs = _get_auth_route_configs(modules)
    api_configs = _get_api_route_configs(modules)
    service_configs = _get_service_route_configs(modules)
    return {**auth_configs, **api_configs, **service_configs}

def _get_auth_route_configs(modules: dict) -> dict:
    """Get authentication route configurations."""
    return {"auth": (modules["auth_router"], "/api/auth", ["auth"]),
        "agent": (modules["agent_router"], "/api/agent", ["agent"])}

def _get_api_route_configs(modules: dict) -> dict:
    """Get API route configurations."""
    return {"threads": (modules["threads_router"], "", ["threads"]),
        "llm_cache": (modules["llm_cache_router"], "/api/llm-cache", ["llm-cache"])}

def _get_service_route_configs(modules: dict) -> dict:
    """Get service route configurations."""
    return {"quality": (modules["quality"].router, "", ["quality"]),
        "websockets": (modules["websockets_router"], "", ["websockets"])}


def _get_business_route_configs(modules: dict) -> dict:
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
            "corpus": (modules["corpus"].router, "/api/corpus", ["corpus"])}


def _get_utility_route_configs(modules: dict) -> dict:
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
            "unified_tools": (modules["unified_tools"].router, "/api/tools", ["unified-tools"])}


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


def _get_route_configurations(modules: dict) -> dict:
    """Get route configuration mapping."""
    core_configs = _get_core_route_configs(modules)
    business_configs = _get_business_route_configs(modules)
    utility_configs = _get_utility_route_configs(modules)
    return {**core_configs, **business_configs, **utility_configs}

def _register_route_modules(app: FastAPI, routes: dict) -> None:
    """Register route modules with the app."""
    for name, (router, prefix, tags) in routes.items():
        app.include_router(router, prefix=prefix, tags=tags)


def setup_root_endpoint(app: FastAPI) -> None:
    """Setup the root API endpoint."""
    from app.logging_config import central_logger
    @app.get("/")
    def read_root():
        logger = central_logger.get_logger(__name__)
        logger.info("Root endpoint was hit.")
        return {"message": "Welcome to Netra API"}


def create_app() -> FastAPI:
    """Create and fully configure the FastAPI application."""
    app = create_fastapi_app()
    _configure_app_handlers(app)
    _configure_app_routes(app)
    return app


def _configure_app_handlers(app: FastAPI) -> None:
    """Configure error handlers and middleware."""
    register_error_handlers(app)
    setup_middleware(app)
    initialize_oauth(app)


def _configure_app_routes(app: FastAPI) -> None:
    """Configure application routes."""
    register_api_routes(app)
    setup_root_endpoint(app)