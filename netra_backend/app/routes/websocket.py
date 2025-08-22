"""
Standard WebSocket endpoint that forwards to secure WebSocket implementation.

This provides backward compatibility for frontends expecting /ws endpoint.

Business Value Justification (BVJ):
- Segment: Platform/Internal  
- Business Goal: Development Velocity
- Value Impact: Ensures frontend WebSocket compatibility
- Strategic Impact: Prevents WebSocket connection failures
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)
router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Standard WebSocket endpoint - forwards to secure implementation.
    
    This endpoint exists for backward compatibility with frontends
    that expect a /ws endpoint. It delegates to the secure WebSocket handler.
    """
    logger.info("WebSocket connection attempt at /ws - forwarding to secure handler")
    
    # Import the secure WebSocket handler
    from netra_backend.app.routes.websocket_secure import secure_websocket_endpoint
    
    # Delegate to secure endpoint  
    await secure_websocket_endpoint(websocket)


@router.websocket("/ws/{user_id}")
async def websocket_endpoint_with_user(websocket: WebSocket, user_id: str):
    """
    WebSocket endpoint with user ID parameter - forwards to secure implementation.
    
    This supports frontend patterns like /ws/v1/{user_id} by extracting the user_id
    and forwarding to the secure endpoint.
    """
    logger.info(f"WebSocket connection attempt at /ws/{user_id} - forwarding to secure handler")
    
    # Add user_id to WebSocket state for the secure handler to use
    websocket.state.user_id_from_path = user_id
    
    # Import the secure WebSocket handler
    from netra_backend.app.routes.websocket_secure import secure_websocket_endpoint
    
    # Delegate to secure endpoint
    await secure_websocket_endpoint(websocket)


@router.websocket("/ws/v1/{user_id}")
async def websocket_endpoint_v1(websocket: WebSocket, user_id: str):
    """
    WebSocket endpoint version 1 with user ID - forwards to secure implementation.
    
    This specifically handles the pattern shown in frontend .env.local:
    NEXT_PUBLIC_WEBSOCKET_URL=ws://localhost:8000/ws/v1/{user_id}
    """
    logger.info(f"WebSocket connection attempt at /ws/v1/{user_id} - forwarding to secure handler")
    
    # Add user_id to WebSocket state for the secure handler to use  
    websocket.state.user_id_from_path = user_id
    
    # Import the secure WebSocket handler
    from netra_backend.app.routes.websocket_secure import secure_websocket_endpoint
    
    # Delegate to secure endpoint
    await secure_websocket_endpoint(websocket)


@router.get("/ws")
async def websocket_info():
    """Information endpoint for WebSocket connection."""
    return JSONResponse({
        "message": "WebSocket endpoints available",
        "endpoints": {
            "/ws": "Standard WebSocket endpoint",
            "/ws/{user_id}": "WebSocket with user ID parameter", 
            "/ws/v1/{user_id}": "WebSocket v1 with user ID parameter",
            "/ws/secure": "Secure WebSocket endpoint with JWT auth"
        },
        "authentication": "Required for all WebSocket connections",
        "auth_methods": ["Authorization header (Bearer token)", "Sec-WebSocket-Protocol"],
        "status": "available"
    })


@router.get("/ws/config")
async def websocket_config():
    """WebSocket configuration endpoint for service discovery."""
    from netra_backend.app.core.configuration import get_configuration
    
    config = get_configuration()
    
    return JSONResponse({
        "websocket_config": {
            "available_endpoints": [
                "/ws",
                "/ws/{user_id}", 
                "/ws/v1/{user_id}",
                "/ws/secure"
            ],
            "authentication_required": True,
            "supported_protocols": ["jwt-auth"],
            "cors_enabled": True,
            "environment": config.environment,
            "max_connections_per_user": 3,
            "heartbeat_interval": 45
        },
        "status": "healthy"
    })