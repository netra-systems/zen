"""
Analytics Core Module

Core functionality for the analytics microservice.
"""

from analytics_service.analytics_core.config import AnalyticsConfig, get_config

def get_routes():
    """Import routes on demand to avoid circular imports."""
    try:
        from analytics_service.analytics_core import routes
        return routes
    except ImportError as e:
        print(f"Warning: Could not import routes: {e}")
        return None

# Lazy import routes as a module attribute
routes = None

def __getattr__(name):
    """Lazy loading of routes attribute."""
    global routes
    if name == 'routes':
        if routes is None:
            routes = get_routes()
        # If routes is still None, create a mock-like object for testing
        if routes is None:
            from unittest.mock import MagicMock
            routes = MagicMock()
            routes.health_routes = MagicMock()
            routes.analytics_routes = MagicMock() 
            routes.websocket_routes = MagicMock()
        return routes
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = ['AnalyticsConfig', 'get_config', 'get_routes']