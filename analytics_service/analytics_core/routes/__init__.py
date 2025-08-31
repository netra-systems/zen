"""
Analytics Service Routes Package
Comprehensive API routes for analytics functionality, health monitoring, and real-time streaming
"""

from .analytics_routes import router as analytics_router
from .health_routes import router as health_router  
from .websocket_routes import router as websocket_router, connection_manager

__all__ = [
    "analytics_router",
    "health_router", 
    "websocket_router",
    "connection_manager"
]