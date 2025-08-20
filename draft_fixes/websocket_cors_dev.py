"""DRAFT: WebSocket CORS configuration fixes for DEV MODE.

This is a simplified CORS configuration specifically designed for development
environments with better localhost handling and debugging.

DO NOT DEPLOY TO PRODUCTION - THIS IS A DRAFT FOR REVIEW
"""

import re
import os
from typing import List, Optional, Dict, Any
from fastapi import WebSocket
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

# DEV MODE CORS configuration - more permissive for development
DEV_WEBSOCKET_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:3001", 
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
    "https://localhost:3000",
    "https://localhost:3001",
    # Additional DEV origins
    "http://localhost:8080",
    "http://localhost:8000",  # For testing backend
    "http://0.0.0.0:3000",    # Docker scenarios
    "http://0.0.0.0:3001"
]

class DevWebSocketCORSHandler:
    """Simplified WebSocket CORS handler for DEV MODE."""
    
    def __init__(self, additional_origins: Optional[List[str]] = None):
        """Initialize DEV CORS handler.
        
        Args:
            additional_origins: Additional origins to allow beyond defaults
        """
        self.allowed_origins = DEV_WEBSOCKET_ORIGINS.copy()
        
        if additional_origins:
            self.allowed_origins.extend(additional_origins)
        
        # Add origins from environment
        env_origins = os.getenv("DEV_WEBSOCKET_ORIGINS", "")
        if env_origins:
            custom_origins = [origin.strip() for origin in env_origins.split(",") if origin.strip()]
            self.allowed_origins.extend(custom_origins)
        
        # Remove duplicates
        self.allowed_origins = list(set(self.allowed_origins))
        
        # Compile patterns for efficient matching
        self._origin_patterns = self._compile_origin_patterns()
        
        logger.info(f"[WebSocket CORS] DEV MODE initialized with {len(self.allowed_origins)} allowed origins")
        logger.debug(f"[WebSocket CORS] Allowed origins: {self.allowed_origins}")
    
    def _compile_origin_patterns(self) -> List[re.Pattern]:
        """Compile origin patterns for efficient matching."""
        patterns = []
        
        for origin in self.allowed_origins:
            if '*' in origin:
                # Convert wildcard to regex
                pattern = origin.replace('*', '.*')
                patterns.append(re.compile(f'^{pattern}$', re.IGNORECASE))
            else:
                # Exact match
                patterns.append(re.compile(f'^{re.escape(origin)}$', re.IGNORECASE))
        
        return patterns
    
    def is_origin_allowed(self, origin: Optional[str]) -> bool:
        """Check if origin is allowed for DEV MODE WebSocket connections.
        
        Args:
            origin: The origin header value
            
        Returns:
            True if origin is allowed, False otherwise
        """
        if not origin:
            # In DEV MODE, we're more lenient about missing origin
            logger.warning("[WebSocket CORS] DEV MODE: No origin header, allowing connection")
            return True
        
        # Check against patterns
        for pattern in self._origin_patterns:
            if pattern.match(origin):
                logger.debug(f"[WebSocket CORS] DEV MODE: Origin allowed: {origin}")
                return True
        
        # DEV MODE: Log denied origin for debugging
        logger.warning(f"[WebSocket CORS] DEV MODE: Origin denied: {origin}")
        logger.debug(f"[WebSocket CORS] DEV MODE: Allowed origins: {self.allowed_origins}")
        
        return False
    
    def get_cors_headers(self, origin: Optional[str]) -> Dict[str, str]:
        """Get CORS headers for WebSocket response.
        
        Args:
            origin: The origin to include in headers
            
        Returns:
            Dictionary of CORS headers
        """
        if not origin:
            origin = "*"  # Fallback for DEV MODE
        
        return {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Authorization, Content-Type, Origin, Accept, X-Requested-With",
            "Vary": "Origin",
            # DEV MODE headers
            "X-WebSocket-CORS-Mode": "development",
            "X-WebSocket-CORS-Timestamp": str(int(__import__('time').time()))
        }
    
    def get_debug_info(self) -> Dict[str, Any]:
        """Get debug information for DEV MODE."""
        return {
            "mode": "development",
            "allowed_origins": self.allowed_origins,
            "patterns_count": len(self._origin_patterns),
            "env_origins": os.getenv("DEV_WEBSOCKET_ORIGINS", "not_set")
        }


def validate_websocket_origin_dev(websocket: WebSocket, cors_handler: DevWebSocketCORSHandler) -> bool:
    """Validate WebSocket connection origin for DEV MODE.
    
    Args:
        websocket: The WebSocket connection
        cors_handler: DEV CORS handler instance
        
    Returns:
        True if origin is valid, False otherwise
    """
    # Extract origin from headers (case-insensitive)
    origin = None
    for header_name, header_value in websocket.headers.items():
        if header_name.lower() == "origin":
            origin = header_value
            break
    
    # Check if origin is allowed
    if not cors_handler.is_origin_allowed(origin):
        logger.error(f"[WebSocket CORS] DEV MODE: Connection denied for origin: {origin}")
        return False
    
    logger.info(f"[WebSocket CORS] DEV MODE: Connection allowed from origin: {origin}")
    return True


def get_dev_cors_handler() -> DevWebSocketCORSHandler:
    """Get DEV MODE WebSocket CORS handler."""
    # Check for additional origins from environment
    additional_origins = []
    
    # Allow custom origins for specific dev scenarios
    custom_origins_env = os.getenv("CUSTOM_DEV_ORIGINS", "")
    if custom_origins_env:
        additional_origins = [origin.strip() for origin in custom_origins_env.split(",") if origin.strip()]
    
    return DevWebSocketCORSHandler(additional_origins)


def check_websocket_cors_dev(websocket: WebSocket) -> bool:
    """Quick CORS check for DEV MODE WebSocket route handlers.
    
    Args:
        websocket: The WebSocket connection
        
    Returns:
        True if CORS is valid, False otherwise
    """
    cors_handler = get_dev_cors_handler()
    return validate_websocket_origin_dev(websocket, cors_handler)


def get_websocket_cors_headers_dev(websocket: WebSocket) -> Dict[str, str]:
    """Get CORS headers for WebSocket response in DEV MODE.
    
    Args:
        websocket: The WebSocket connection
        
    Returns:
        Dictionary of CORS headers
    """
    cors_handler = get_dev_cors_handler()
    
    # Extract origin
    origin = None
    for header_name, header_value in websocket.headers.items():
        if header_name.lower() == "origin":
            origin = header_value
            break
    
    if cors_handler.is_origin_allowed(origin):
        return cors_handler.get_cors_headers(origin)
    
    return {}


# DEV MODE: Simple debugging utility
def debug_websocket_headers(websocket: WebSocket) -> Dict[str, Any]:
    """Debug utility to inspect WebSocket headers.
    
    Args:
        websocket: The WebSocket connection
        
    Returns:
        Dictionary with header information for debugging
    """
    headers_info = {
        "all_headers": dict(websocket.headers),
        "origin": websocket.headers.get("origin"),
        "user_agent": websocket.headers.get("user-agent"),
        "host": websocket.headers.get("host"),
        "connection": websocket.headers.get("connection"),
        "upgrade": websocket.headers.get("upgrade"),
        "sec_websocket_key": websocket.headers.get("sec-websocket-key", "present" if websocket.headers.get("sec-websocket-key") else "missing"),
        "sec_websocket_version": websocket.headers.get("sec-websocket-version"),
        "query_params": dict(websocket.query_params),
        "client_info": {
            "host": websocket.client.host if websocket.client else "unknown",
            "port": websocket.client.port if websocket.client else "unknown"
        }
    }
    
    logger.debug(f"[WebSocket CORS] DEV MODE: Headers debug info: {headers_info}")
    return headers_info


# Global DEV CORS handler instance
_dev_cors_handler: Optional[DevWebSocketCORSHandler] = None

def get_global_dev_cors_handler() -> DevWebSocketCORSHandler:
    """Get global DEV MODE WebSocket CORS handler instance."""
    global _dev_cors_handler
    
    if _dev_cors_handler is None:
        _dev_cors_handler = get_dev_cors_handler()
    
    return _dev_cors_handler