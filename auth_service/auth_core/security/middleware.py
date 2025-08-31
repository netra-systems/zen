"""
Auth Service Security Middleware - Canonical Security Implementation
SSOT for all auth service security middleware functionality
"""
import logging
from typing import Optional, Dict, Any
from fastapi import Request
from fastapi.responses import JSONResponse

from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)

# Security constants
MAX_JSON_PAYLOAD_SIZE = 50 * 1024  # 50KB


async def validate_request_size(request: Request) -> Optional[JSONResponse]:
    """
    Canonical request size validation logic - SSOT for auth service
    
    Args:
        request: FastAPI request object
        
    Returns:
        JSONResponse with error if request is invalid, None if valid
    """
    content_length = request.headers.get("content-length")
    content_type = request.headers.get("content-type", "")
    
    if content_length and "json" in content_type.lower():
        try:
            size = int(content_length)
            if size > MAX_JSON_PAYLOAD_SIZE:
                logger.warning(f"Request payload too large: {size} bytes (max: {MAX_JSON_PAYLOAD_SIZE})")
                return JSONResponse(
                    status_code=413,  # Payload Too Large
                    content={"detail": f"Request payload too large. Maximum size: {MAX_JSON_PAYLOAD_SIZE} bytes"}
                )
        except ValueError:
            # Invalid Content-Length header
            logger.warning(f"Invalid Content-Length header: {content_length}")
            return JSONResponse(
                status_code=400,
                content={"detail": "Invalid Content-Length header"}
            )
    
    return None


def add_service_headers(response, service_name: str = "auth-service", service_version: str = "1.0.0"):
    """
    Add service identification headers
    
    Args:
        response: FastAPI response object
        service_name: Name of the service
        service_version: Version of the service
    """
    response.headers["X-Service-Name"] = service_name
    response.headers["X-Service-Version"] = service_version


def add_security_headers(response):
    """
    Add security headers when enabled in environment
    
    Args:
        response: FastAPI response object
    """
    if get_env().get("SECURE_HEADERS_ENABLED", "false").lower() == "true":
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"


async def create_security_middleware(
    add_service_headers_flag: bool = True,
    add_security_headers_flag: bool = True,
    service_name: str = "auth-service",
    service_version: str = "1.0.0"
):
    """
    Factory function to create security middleware with configurable features
    
    Args:
        add_service_headers_flag: Whether to add service identification headers
        add_security_headers_flag: Whether to add security headers
        service_name: Service name for headers
        service_version: Service version for headers
        
    Returns:
        Configured middleware function
    """
    async def security_middleware(request: Request, call_next):
        """Consolidated security middleware - canonical implementation"""
        # Request size validation (always enabled)
        size_error = await validate_request_size(request)
        if size_error:
            return size_error
        
        # Process request
        response = await call_next(request)
        
        # Add headers as configured
        if add_service_headers_flag:
            add_service_headers(response, service_name, service_version)
        
        if add_security_headers_flag:
            add_security_headers(response)
        
        return response
    
    return security_middleware